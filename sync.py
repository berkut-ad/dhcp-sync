import logging
import argparse
import config
from datetime import datetime, timezone

from dhcp_parser import parse_leases
from lease_db import init_db, get_all_leases, update_lease, delete_lease
from netbox_sync import sync_lease, expire_lease

def setup_logging(debug=False, dry_run=False, log_file=None, dryrun_log_file=None):
    log_path = dryrun_log_file if dry_run else log_file
    log_level = logging.DEBUG if debug else logging.INFO

    # Remove all handlers associated with the root logger.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

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
    verify_ssl = not args.no_verify_ssl

    current_ips = set()

    for lease in current_leases:
        logging.debug(f"Lease from parser: {lease}")
        ip = lease["ip"]
        current_ips.add(ip)
        old = old_leases.get(ip)

        if args.only_expired:
            continue

        if not old:
            logging.info(f"*** NEW lease: {ip} -> {lease['mac']}")
            if not args.dry_run:
                sync_lease(lease, args.netbox_url, args.netbox_token, verify_ssl=verify_ssl)
        elif old["mac"] != lease["mac"]:
            logging.info(f"### REASSIGNED: {ip} {old['mac']} → {lease['mac']}")
            if not args.dry_run:
                sync_lease(lease, args.netbox_url, args.netbox_token, verify_ssl=verify_ssl)
        elif old["hostname"] != lease["hostname"]:
            logging.info(f"### UPDATED hostname: {ip} {old['hostname']} → {lease['hostname']}")
            if not args.dry_run:
                sync_lease(lease, args.netbox_url, args.netbox_token, verify_ssl=verify_ssl)

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
                        expire_lease(ip, args.netbox_url, args.netbox_token, verify_ssl=verify_ssl)
                        delete_lease(conn, ip)

    logging.info("--> Finished DHCP sync")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DHCP Lease Sync to NetBox")

    # Debug/Dry-run/Selective
    parser.add_argument("--debug", action="store_true", help="Enable debug logging to console")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to NetBox or DB")
    parser.add_argument("--only-expired", action="store_true", help="Only expire old leases")
    parser.add_argument("--only-new", action="store_true", help="Only create/update active leases")
    parser.add_argument("--no-verify-ssl", action="store_true", help="Disable SSL certificate verification (insecure)")

    # Overrides
    parser.add_argument("--leases-file", default=config.LEASES_FILE, help="Path to dhcpd.leases file")
    parser.add_argument("--db-path", default=config.SQLITE_DB, help="Path to lease state SQLite DB")
    parser.add_argument("--netbox-url", default=config.NETBOX_URL, help="NetBox API base URL")
    parser.add_argument("--netbox-token", default=config.NETBOX_TOKEN, help="NetBox API token")
    parser.add_argument("--log-file", default=config.LOG_FILE, help="Path to standard log file")
    parser.add_argument("--dryrun-log-file", default=config.DRYRUN_LOG_FILE, help="Path to dry-run log file")

    args = parser.parse_args()
    main(args)
