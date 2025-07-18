import sqlite3
from datetime import datetime

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS leases (
            ip TEXT PRIMARY KEY,
            mac TEXT,
            hostname TEXT,
            expiry TEXT
        )
    ''')
    conn.commit()
    return conn

def get_all_leases(conn):
    c = conn.cursor()
    c.execute("SELECT ip, mac, hostname, expiry FROM leases")
    rows = c.fetchall()
    return {row[0]: {"mac": row[1], "hostname": row[2], "expiry": row[3]} for row in rows}

def update_lease(conn, lease):
    c = conn.cursor()
    c.execute('''
        INSERT INTO leases (ip, mac, hostname, expiry)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(ip) DO UPDATE SET
            mac=excluded.mac,
            hostname=excluded.hostname,
            expiry=excluded.expiry
    ''', (lease["ip"], lease["mac"], lease["hostname"], lease["lease_expiry"]))
    conn.commit()

def delete_lease(conn, ip):
    c = conn.cursor()
    c.execute("DELETE FROM leases WHERE ip = ?", (ip,))
    conn.commit()
