NETBOX_URL = "http://netbox.local/api/"
NETBOX_TOKEN = "YOUR_NETBOX_TOKEN"

LEASES_FILE = "/var/lib/dhcp/dhcpd.leases"
SQLITE_DB = "./leases.db"
LOG_FILE = "./sync.log"
DRYRUN_LOG_FILE = "./sync-dryrun.log"

# To accomodate Self signed cert:
VERIFY_SSL = False  # Set False to disable SSL verification (not recommended for prod)