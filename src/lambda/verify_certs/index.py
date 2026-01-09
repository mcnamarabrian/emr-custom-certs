import socket
import ssl
from cryptography import x509
from cryptography.x509.oid import NameOID

# Services that SHOULD have TLS with custom certificates
# These are the HTTPS web UIs and TLS-enabled data ports
TLS_SERVICES = {
    "primary": [
        (9871, "NameNode HTTPS UI", True),
        (8090, "ResourceManager HTTPS UI", True),
        (18480, "Spark History Server HTTPS", True),
        (8480, "JournalNode HTTPS", False),  # May not be running
        (19890, "Job History Server HTTPS", False),  # May not be running
    ],
    "core": [
        (9865, "DataNode HTTPS", True),
        (8044, "NodeManager HTTPS UI", False),  # May not be running
    ]
}

# Mapping of OIDs to short names
OID_MAP = {
    NameOID.COMMON_NAME: 'CN',
    NameOID.ORGANIZATION_NAME: 'O',
    NameOID.ORGANIZATIONAL_UNIT_NAME: 'OU',
    NameOID.COUNTRY_NAME: 'C',
    NameOID.STATE_OR_PROVINCE_NAME: 'ST',
    NameOID.LOCALITY_NAME: 'L',
}


def extract_name_attributes(name):
    """Extract certificate name attributes into a dict."""
    details = {}
    for oid, short_name in OID_MAP.items():
        try:
            attr = name.get_attributes_for_oid(oid)
            if attr:
                details[short_name] = attr[0].value
        except Exception:
            pass
    return details


def check_tls_cert(host, port, expected_ca, timeout=5):
    """Check TLS certificate on a host:port and verify issuer."""
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE  # We just want to see the cert

        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert_der = ssock.getpeercert(binary_form=True)

                # Parse certificate using cryptography library
                cert = x509.load_der_x509_certificate(cert_der)

                # Extract subject and issuer details
                subject_details = extract_name_attributes(cert.subject)
                issuer_details = extract_name_attributes(cert.issuer)

                issuer_cn = issuer_details.get('CN', 'Unknown')

                # Get validity dates
                not_before = cert.not_valid_before_utc.strftime('%Y-%m-%d %H:%M:%S UTC')
                not_after = cert.not_valid_after_utc.strftime('%Y-%m-%d %H:%M:%S UTC')

                result = {
                    "issuer": issuer_details,
                    "subject": subject_details,
                    "validity": {
                        "notBefore": not_before,
                        "notAfter": not_after
                    }
                }

                if expected_ca and expected_ca in issuer_cn:
                    result["status"] = "PASS"
                    result["message"] = "Custom CA certificate verified"
                elif expected_ca:
                    result["status"] = "WARN"
                    result["message"] = "TLS enabled but different CA"
                else:
                    result["status"] = "PASS"
                    result["message"] = "TLS enabled"

                return result

    except socket.timeout:
        return {"status": "SKIP", "message": "Connection timeout - service may not be running"}
    except ConnectionRefusedError:
        return {"status": "SKIP", "message": "Service not running on this port"}
    except ssl.SSLError as e:
        err_str = str(e)
        if "UNEXPECTED_EOF" in err_str or "EOF occurred" in err_str:
            return {"status": "INFO", "message": "Port open but not TLS (uses RPC/binary protocol)"}
        elif "WRONG_VERSION" in err_str:
            return {"status": "INFO", "message": "Port open but not TLS-enabled"}
        else:
            return {"status": "SKIP", "message": f"SSL error: {err_str[:60]}"}
    except Exception as e:
        err_str = str(e)
        if "null byte" in err_str.lower():
            return {"status": "INFO", "message": "Port open but uses binary protocol (not TLS)"}
        return {"status": "SKIP", "message": f"Error: {err_str[:60]}"}


def handler(event, context):  # noqa: ARG001 - context required by Lambda
    primary_dns = event.get('primary_dns')
    core_dns = event.get('core_dns')
    expected_ca = event.get('expected_ca', '')

    results = {
        "primary_node": primary_dns,
        "core_node": core_dns,
        "expected_ca": expected_ca,
        "primary_results": [],
        "core_results": [],
        "summary": {"pass": 0, "warn": 0, "info": 0, "skip": 0}
    }

    # Check primary node TLS services
    if primary_dns:
        for port, service, required in TLS_SERVICES["primary"]:
            result = check_tls_cert(primary_dns, port, expected_ca)
            result_entry = {
                "service": service,
                "port": port,
                "status": result["status"],
                "message": result["message"],
                "required": required
            }
            # Include certificate details if available
            for key in ["issuer", "subject", "validity"]:
                if key in result:
                    result_entry[key] = result[key]
            results["primary_results"].append(result_entry)
            results["summary"][result["status"].lower()] += 1

    # Check core node TLS services
    if core_dns and core_dns != "None":
        for port, service, required in TLS_SERVICES["core"]:
            result = check_tls_cert(core_dns, port, expected_ca)
            result_entry = {
                "service": service,
                "port": port,
                "status": result["status"],
                "message": result["message"],
                "required": required
            }
            # Include certificate details if available
            for key in ["issuer", "subject", "validity"]:
                if key in result:
                    result_entry[key] = result[key]
            results["core_results"].append(result_entry)
            results["summary"][result["status"].lower()] += 1

    return results
