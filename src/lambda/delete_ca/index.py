import boto3
import cfnresponse

def handler(event, context):
    ca_arn = event['ResourceProperties']['CertificateAuthorityArn']

    if event['RequestType'] == 'Delete':
        try:
            client = boto3.client('acm-pca')

            # Get CA status
            response = client.describe_certificate_authority(
                CertificateAuthorityArn=ca_arn
            )
            status = response['CertificateAuthority']['Status']

            # Disable CA if active
            if status == 'ACTIVE':
                client.update_certificate_authority(
                    CertificateAuthorityArn=ca_arn,
                    Status='DISABLED'
                )
                print(f"Disabled CA: {ca_arn}")

            # Schedule deletion (minimum 7 days)
            if status not in ['DELETED', 'PENDING_CERTIFICATE']:
                client.delete_certificate_authority(
                    CertificateAuthorityArn=ca_arn,
                    PermanentDeletionTimeInDays=7
                )
                print(f"Scheduled CA for deletion: {ca_arn}")

            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
        except Exception as e:
            print(f"Error deleting CA: {e}")
            cfnresponse.send(event, context, cfnresponse.FAILED, {'Error': str(e)})
    else:
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})