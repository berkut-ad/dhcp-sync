from isc_dhcp_leases import IscDhcpLeases
from datetime import timezone

def parse_leases(file_path):
    leases = IscDhcpLeases(file_path).get()
    parsed = []

    for lease in leases:
        expiry = lease.end.replace(tzinfo=timezone.utc).isoformat() if lease.end else None
        parsed.append({
            "ip": lease.ip,
            "mac": lease.hardware,
            "hostname": lease.hostname or "",
            "lease_expiry": expiry
        })

    return parsed
