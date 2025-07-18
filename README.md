**NetBox is configured to accept and store the lease data**
Here are the **prerequisites** you should configure in NetBox:

## 1. **Prerequisites:  Create Custom Fields**

###  The script uses `custom_fields` to store `mac_address` and `lease_expiry` on each IP address object.

### Steps to Create:

Navigate in the NetBox UI:

**Admin > Custom Fields > Add Custom Field OR Customization > Custom Fields**

#### a. `mac_address`

* **Model**: `ipam | IP address`
* **Type**: Text
* **Label**: MAC Address
* **Required**: No

#### b. `lease_expiry`

* **Model**: `ipam | IP address`
* **Type**: DateTime
* **Label**: Lease Expiry
* **Required**: No

### **Create Tag: `dhcp`**

The script assigns a `dhcp` tag to identify dynamically leased IPs.

### How to Create:

**Navigate**:
**IPAM > Tags > Add**

* **Name**: `dhcp`
* **Slug**: `dhcp`
* **Color**: (optional)


## 2. **Prerequisites: Permissions / Token Scope**

Make sure the API **Token** you're using has permission to:

* **Create**, **update**, and **view** `IP address` records.
* (Optional) Manage `tags` and `custom_fields` if you're doing this via API.

* Go to **Admin > Users > Tokens**
* Ensure token has scope:

  * `ipam.ipaddress: add, change, view`
  * `extras.tag: view`
  * `extras.customfield: view` (needed for script tag/CF creation)


## 3. Prerequisites: Pre-create Subnets

If your IP addresses fall under existing subnets in NetBox (`ipam > prefixes`), it improves searchability and hierarchy.


## 4. Prerequisites: Custom Statuses

If you want more granular control over status (e.g., `leased`, `expired`, etc.), you can:

* Go to **Admin > Choices > IP Address status**
* Add custom statuses (requires advanced NetBox config)

But for now, the script just uses:

* `active` for live DHCP lease
* `reserved` for expired

## Summary Checklist

| Item                        | Required | Notes                                    |
| --------------------------- | -------- | ---------------------------------------- |
| `mac_address` custom field  | Yes     | Text field for tracking MACs             |
| `lease_expiry` custom field | Yes     | DateTime field                           |
| `dhcp` tag                  | Yes     | To mark dynamic IPs                      |
| API Token w/ permission     | Yes     | Must have `add`, `change`, `view` on IPs |
| Subnets in NetBox           | No      | Optional but improves context            |
| NetBox URL/API reachable    | Yes     | Script must reach NetBox URL             |

---

## 5. Additional Tasks

- Create necessary prefixes, VRFs, and sites in NetBox.
- Create `dhcp` tag in NetBox (change tag used in script).
- IPs are added as `/32` with status **active**.
- Model lease time using custom fields (requires NetBox config).
- If using tags, make sure the tags already exist or enable auto-tagging.
- For tenant/customer-specific DHCP scopes (e.g., Cogent), use VRFs or tenants.

## 6. File Structure

```
dhcp_sync/
├── dhcp_parser.py       # Parses dhcpd.leases into usable dicts
├── lease_db.py          # Manages lease state in SQLite
├── netbox_sync.py       # Sync logic: create/update/expire
├── sync.py              # Main entry point
├── config.py            # API tokens, file paths, etc.
└── sync.log             # Log file
```

## 7. Install dependencies:

```bash
pip install -r requirements.txt
```

## 8. NetBox Sync Script Overview

- Parse `dhcpd.leases` file.
- Store lease state in a local SQLite database.
- Detect changes: new leases, reassignments (IP to new MAC), and expirations.
- Log events to a rotating log file (`sync.log`).
- Sync changes with NetBox.

### Syncing Logic

- Parse current leases from `dhcp_parser`.
- Load stored leases from SQLite (`lease_db`).
- Sync deltas to NetBox.
- Log changes.

### Flags

- `--debug`: Show verbose log output to console.
- `--dry-run`: Simulate actions, don’t write to NetBox or DB.
- `--only-expired`: Only process expired leases.
- `--only-new`: Only process new leases.
- `--no-verify-ssl`: Disable SSL certificate verification (insecure).

### CLI Overrides

- `--leases-file`
- `--netbox-url`
- `--netbox-token`
- `--db-path`

### Execution

- Run: `python3 sync.py`
- Can be scheduled via cron or systemd.

#### Examples

**Normal mode (sync everything):**
```bash
python3 sync.py
```

**Show all logs to console:**
```bash
python3 sync.py --debug
```

**Simulate without making changes (Dry-run logs go to a separate file `sync-dryrun.log`):**
```bash
python3 sync.py --dry-run
```

**Only clean up expired leases:**
```bash
python3 sync.py --only-expired
```

**Only process active leases (ignore expired ones):**
```bash
python3 sync.py --only-new
```
