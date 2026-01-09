# EMR Custom TLS Certificates

A minimal PySpark "Hello World" project demonstrating Amazon EMR 7.9 with custom TLS certificates for in-transit encryption using AWS Private CA.

## Architecture

```mermaid
C4Context
    title EMR Custom TLS Certificates - System Context

    Person(operator, "Operator", "Deploys infrastructure and submits Spark jobs")

    Enterprise_Boundary(aws, "AWS Cloud") {
        System_Boundary(vpc, "VPC (10.0.0.0/16)") {
            Container_Boundary(public, "Public Subnet") {
                Container(nat, "NAT Gateway", "AWS NAT", "Outbound internet for private subnet")
            }

            Container_Boundary(private, "Private Subnet") {
                Container(primary, "EMR Primary", "m5.xlarge", "HDFS NameNode, YARN ResourceManager, Spark History Server")
                Container(core, "EMR Core", "m5.xlarge", "HDFS DataNode, YARN NodeManager")
                Container(lambda, "Verify Certs Lambda", "Python 3.12", "Verifies TLS certificates on EMR nodes")
            }
        }

        System_Ext(pca, "AWS Private CA", "Issues TLS certificates for EMR nodes")
        SystemDb(s3, "S3 Bucket", "Stores logs, scripts, and certificate bundle")
    }

    Rel(operator, lambda, "Invokes", "AWS CLI")
    Rel(operator, s3, "Uploads scripts", "AWS CLI")
    Rel(lambda, primary, "Verifies TLS certs", "SSL/TLS")
    Rel(lambda, core, "Verifies TLS certs", "SSL/TLS")
    Rel(primary, core, "TLS encrypted", "Custom CA certs")
    Rel(primary, s3, "Reads scripts, writes logs", "HTTPS")
    Rel(core, s3, "Writes logs", "HTTPS")
    Rel(primary, pca, "Obtains certificates", "ACM PCA API")
    Rel(private, nat, "Outbound traffic", "")
```

### Components

- **VPC**: Public and private subnets with NAT Gateway
- **AWS Private CA**: Root CA for issuing TLS certificates
- **EMR Cluster**: 1 primary + 1 core node (m5.xlarge) with TLS encryption enabled
- **S3 Bucket**: Stores EMR logs, scripts, and certificate bundle
- **Lambda Function**: Verifies TLS certificates on EMR nodes from within the VPC

## Prerequisites

- [mise](https://mise.jdx.dev/) installed
- AWS credentials configured with appropriate permissions

## Quick Start

### 1. Install dependencies

```bash
mise trust
mise install
```

### 2. Deploy base infrastructure

```bash
mise run deploy
```

This creates VPC, Private CA, S3 bucket, Lambda functions, IAM roles, and security groups.

### 3. Activate the Private CA

After the stack is created, the Private CA needs a root certificate:

```bash
mise run create-ca-cert
```

### 4. Generate and upload EMR certificates

```bash
mise run generate-certs
```

### 5. Deploy EMR cluster

Now that certificates exist, deploy the EMR cluster:

```bash
mise run deploy-emr
```

### 6. Submit the sample PySpark job

```bash
mise run submit-job
```

### 7. Monitor the cluster

```bash
mise run cluster-status
mise run logs
```

### 8. View job output

```bash
mise run step-output
```

### 9. Verify TLS certificates

```bash
mise run verify-certs
```

## Available Tasks

| Task | Description |
|------|-------------|
| `mise run validate` | Validate SAM template |
| `mise run build` | Build SAM application |
| `mise run deploy` | Deploy base infrastructure stack |
| `mise run deploy-guided` | Deploy with interactive prompts |
| `mise run delete` | Delete the base infrastructure stack |
| `mise run outputs` | Get stack outputs |
| `mise run create-ca-cert` | Issue and install CA root certificate |
| `mise run generate-certs` | Generate EMR certificate bundle |
| `mise run deploy-emr` | Deploy EMR cluster (after certs exist) |
| `mise run delete-emr` | Delete EMR cluster stack |
| `mise run submit-job` | Submit PySpark job to EMR |
| `mise run step-output` | Get output from most recent EMR step |
| `mise run cluster-status` | Get EMR cluster status |
| `mise run logs` | View EMR cluster logs |
| `mise run verify-certs` | Verify TLS certificates on EMR nodes |

## Project Structure

```
.
├── .mise/
│   └── tasks/           # Mise task scripts
├── src/
│   └── hello_world.py   # Sample PySpark application
├── mise.toml            # Mise configuration
├── template.yaml        # Base infrastructure (VPC, CA, IAM, etc.)
├── emr-template.yaml    # EMR cluster template
└── README.md
```

## Two-Stack Architecture

The project uses two CloudFormation stacks:

1. **Base Stack** (`emr-custom-certs`): VPC, subnets, NAT Gateway, Private CA, S3 bucket, Lambda functions, IAM roles, and security groups

2. **EMR Stack** (`emr-custom-certs-cluster`): EMR security configuration and cluster, imports values from base stack

This separation allows you to:
- Generate certificates after base infrastructure exists
- Deploy EMR cluster only after certificates are ready
- Delete/recreate EMR cluster without affecting base infrastructure

## TLS Certificate Flow

1. Deploy base stack (creates Private CA in `PENDING_CERTIFICATE` state)
2. `create-ca-cert` task issues a self-signed root certificate
3. `generate-certs` task:
   - Generates a private key
   - Creates a CSR for `*.ec2.internal`
   - Issues an end-entity certificate from the Private CA
   - Bundles everything into `emr-certs.zip`
   - Uploads to S3
4. Deploy EMR stack with security configuration referencing the certificate bundle
5. EMR nodes use the certificates for TLS communication

## Customizing the Private CA

The Private CA subject information is defined in `template.yaml`. Edit the `PrivateCA` resource before running `mise run deploy`:

```yaml
PrivateCA:
  Type: AWS::ACMPCA::CertificateAuthority
  Properties:
    Subject:
      CommonName: !Sub ${AWS::StackName}-emr-ca
      Organization: Your Company Name
      OrganizationalUnit: Engineering
      Country: Your Country
      State: Your State
      Locality: Your City
```

Available subject fields:
- `CommonName` - CA identifier (default includes stack name)
- `Organization` - Company or organization name
- `OrganizationalUnit` - Department or team
- `Country` - Two-letter country code (e.g., US, GB, DE)
- `State` - State or province
- `Locality` - City

These values are embedded in the root CA certificate and appear in all certificates issued by the CA. Customize them before the initial deployment—changing them later requires recreating the Private CA.

## Costs

This project creates billable AWS resources:

- **NAT Gateway**: ~$0.045/hour + data transfer
- **Private CA**: ~$400/month (first month prorated)
- **EMR Cluster**: 2x m5.xlarge (~$0.192/hour each)
- **Lambda Functions**: Minimal cost (only invoked on-demand)

**Important**: Delete resources when not in use:

```bash
mise run delete-emr   # Delete EMR cluster first
mise run delete       # Delete base infrastructure
```

## Cleanup

```bash
# Delete EMR cluster stack first
mise run delete-emr

# Delete the base infrastructure stack
mise run delete
```

The S3 bucket contents and Private CA are automatically cleaned up when the stack is deleted. The Private CA is scheduled for permanent deletion after 7 days (the minimum allowed by AWS).

## References

- [Encrypt data in transit using a TLS custom certificate provider with Amazon EMR](https://aws.amazon.com/blogs/big-data/encrypt-data-in-transit-using-a-tls-custom-certificate-provider-with-amazon-emr/)
- [EMR Security Configuration](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-create-security-configuration.html)
- [AWS Private CA Documentation](https://docs.aws.amazon.com/privateca/latest/userguide/PcaWelcome.html)
