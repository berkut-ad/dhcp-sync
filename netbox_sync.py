import requests
import json
import logging

def build_headers(token):
    return {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

def sync_lease(lease, netbox_url, token, verify_ssl=True):
    """Create or update IP address in NetBox for a given DHCP lease."""
    ip = lease["ip"]
    mac = lease["mac"]
    dns = lease.get("hostname", "")
    expiry = lease.get("lease_expiry")

    headers = build_headers(token)
    base_url = f"{netbox_url.rstrip('/')}/ipam/ip-addresses/"

    payload = {
        "address": f"{ip}/32",
        "status": "active",
        "dns_name": dns,
        "description": f"DHCP lease for {dns}",
        "tags": [{"name": "dhcp"}],
        "custom_fields": {
            "mac_address": mac,
            "lease_expiry": expiry
        }
    }

    # Check if the IP already exists
    try:
        r = requests.get(f"{base_url}?address={ip}/32", headers=headers, verify=verify_ssl)
        r.raise_for_status()
        results = r.json().get("results", [])

        if results:
            # Update existing record
            ip_id = results[0]["id"]
            update_url = f"{base_url}{ip_id}/"
            r = requests.patch(update_url, headers=headers, data=json.dumps(payload), verify=verify_ssl)
            if r.status_code == 200:
                logging.debug(f"Updated NetBox IP: {ip}")
            else:
                logging.error(f"Failed to update IP {ip}: {r.status_code} {r.text}")
        else:
            # Create new IP
            r = requests.post(base_url, headers=headers, data=json.dumps(payload), verify=verify_ssl)
            if r.status_code == 201:
                logging.debug(f"Created NetBox IP: {ip}")
            else:
                logging.error(f"Failed to create IP {ip}: {r.status_code} {r.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error syncing lease for {ip}: {e}")

def expire_lease(ip, netbox_url, token, verify_ssl=True):
    """Mark a lease as expired in NetBox (change status and remove tags)."""
    headers = build_headers(token)
    base_url = f"{netbox_url.rstrip('/')}/ipam/ip-addresses/"

    try:
        r = requests.get(f"{base_url}?address={ip}/32", headers=headers, verify=verify_ssl)
        r.raise_for_status()
        results = r.json().get("results", [])

        if not results:
            logging.warning(f"IP {ip} not found in NetBox for expiration")
            return

        ip_id = results[0]["id"]
        update_payload = {
            "status": "reserved",
            "tags": [],
            "description": f"Expired DHCP lease"
        }
        update_url = f"{base_url}{ip_id}/"
        r = requests.patch(update_url, headers=headers, data=json.dumps(update_payload), verify=verify_ssl)

        if r.status_code == 200:
            logging.debug(f"Marked IP {ip} as expired in NetBox")
        else:
            logging.error(f"Failed to mark IP {ip} as expired: {r.status_code} {r.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error expiring lease {ip}: {e}")
