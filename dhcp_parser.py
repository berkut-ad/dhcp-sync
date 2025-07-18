from isc_dhcp_leases import IscDhcpLeases
from datetime import timezone

def parse_leases(file_path):
    leases = IscDhcpLeases(file_path).get_current()
    parsed = []

    for lease in leases.values():
        expiry = lease.end.replace(tzinfo=timezone.utc).isoformat()
        parsed.append({
            "ip": lease.ip,
            "mac": lease.ethernet,
            "hostname": lease.hostname or "",
            "lease_expiry": expiry
        })

    return parsed
