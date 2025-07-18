import logging
import argparse
from datetime import datetime, timezone

from dhcp_parser import parse_leases
from lease_db import init_db, get_all_leases, update_lease, delete_lease
from netbox_sync import sync_lease, expire_lease

# === Default config (can be overridden via CLI) ===
DEFAULT_CONFIG = {
    "netbox_url": "http://netbox.local/api/",
    "netbox_token": "YOUR_NETBOX_TOKEN",
    "leases_file": "/var/lib/dhcp/dhcpd.leases",
    "db_path": "./leases.db",
    "log_file": "./sync.log",
    "dryrun_log_file": "./sync-dryrun.log"
}

def setup_logging(debug=False, dry_run=False, log_file=None, dryrun_log_file=None):
    log_path = dryrun_log_file if dry_run else log_file
    log_level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        filename=log_path,
        level=log_level,
        format="%(asctime)s %(levelname)s: %(message)s"
    )
    if debug:
        # Also log to console
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        console.setFormatter(formatter)
        logging.getLogger().addHandler(console)

def main(args):
    setup_logging(args.debug, args.dry_run, args.log_file, args.dryrun_log_file)
    logging.info("--> Starting DHCP sync")

    conn = init_db(args.db_path)
    current_leases = parse_leases(args.leases_file)
    old_leases = get_all_leases(conn)

    current_ips = set()

    for lease in current_leases:
        ip = lease["ip"]
        current_ips.add(ip)
        old = old_leases.get(ip)

        if args.only_expired:
            continue

        if not old:
            logging.info(f"*** NEW lease: {ip} -> {lease['mac']}")
            if not args.dry_run:
                sync_lease(lease, args.netbox_url, args.netbox_token)
        elif old["mac"] != lease["mac"]:
            logging.info(f"### REASSIGNED: {ip} {old['mac']} → {lease['mac']}")
            if not args.dry_run:
                sync_lease(lease, args.netbox_url, args.netbox_token)
        elif old["hostname"] != lease["hostname"]:
            logging.info(f"### UPDATED hostname: {ip} {old['hostname']} → {lease['hostname']}")
            if not args.dry_run:
                sync_lease(lease, args.netbox_url, args.netbox_token)

        if not args.dry_run:
            update_lease(conn, lease)

    # Process expired leases
    if not args.only_new:
        now = datetime.now(timezone.utc)
        for ip, data in old_leases.items():
            if ip not in current_ips:
                expiry = datetime.fromisoformat(data["expiry"])
                if expiry < now:
                    logging.info(f"XXX EXPIRED: {ip}")
                    if not args.dry_run:
                        expire_lease(ip, args.netbox_url, args.netbox_token)
                        delete_lease(conn, ip)

    logging.info("--> Finished DHCP sync")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DHCP Lease Sync to NetBox")

    # Debug/Dry-run/Selective
    parser.add_argument("--debug", action="store_true", help="Enable debug logging to console")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to NetBox or DB")
    parser.add_argument("--only-expired", action="store_true", help="Only expire old leases")
    parser.add_argument("--only-new", action="store_true", help="Only create/update active leases")

    # Overrides
    parser.add_argument("--leases-file", default=DEFAULT_CONFIG["leases_file"], help="Path to dhcpd.leases file")
    parser.add_argument("--db-path", default=DEFAULT_CONFIG["db_path"], help="Path to lease state SQLite DB")
    parser.add_argument("--netbox-url", default=DEFAULT_CONFIG["netbox_url"], help="NetBox API base URL")
    parser.add_argument("--netbox-token", default=DEFAULT_CONFIG["netbox_token"], help="NetBox API token")
    parser.add_argument("--log-file", default=DEFAULT_CONFIG["log_file"], help="Path to standard log file")
    parser.add_argument("--dryrun-log-file", default=DEFAULT_CONFIG["dryrun_log_file"], help="Path to dry-run log file")

    args = parser.parse_args()
    main(args)
