"""
Migration: add company_name column to clients table.
Idempotent — safe to run multiple times.
"""
import os
import sqlite3

DATA_DIR = os.environ.get("DATA_DIR", ".")
DB_PATH = os.path.join(DATA_DIR, "ledger.db")

conn = sqlite3.connect(DB_PATH)
cols = [row[1] for row in conn.execute("PRAGMA table_info(clients)").fetchall()]
if "company_name" not in cols:
    conn.execute("ALTER TABLE clients ADD COLUMN company_name TEXT")
    conn.commit()
    print("✓ Added company_name column to clients.")
else:
    print("company_name already exists — nothing to do.")
conn.close()
