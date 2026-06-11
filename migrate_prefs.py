#!/usr/bin/env python3
"""
Idempotent migration: add view preference columns to users table.

Usage:
  python migrate_prefs.py /path/to/ledger.db
"""
import sqlite3
import sys
import os

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), 'ledger.db')

print(f"Migrating: {DB_PATH}")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

existing = {r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()}

new_cols = [
    ('view_pref_clients',   "TEXT NOT NULL DEFAULT 'list'"),
    ('view_pref_documents', "TEXT NOT NULL DEFAULT 'list'"),
    ('view_pref_jobs',      "TEXT NOT NULL DEFAULT 'list'"),
]

added = []
for col, defn in new_cols:
    if col not in existing:
        c.execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")
        added.append(col)

conn.commit()
conn.close()

if added:
    print(f"Done. Added columns: {', '.join(added)}")
else:
    print("Already up to date — no changes needed.")
