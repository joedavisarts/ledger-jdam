#!/usr/bin/env python3
"""
migrate_jobnumbers.py — idempotent migration for job numbering feature.

Usage:
    python3 migrate_jobnumbers.py [path/to/ledger.db]
"""

import os
import sqlite3
import sys


def run(db_path):
    print(f"Using database: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    # ------------------------------------------------------------------ #
    # 1. Add job_prefix column to users if not present
    # ------------------------------------------------------------------ #
    cols = [r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()]
    if 'job_prefix' not in cols:
        c.execute("ALTER TABLE users ADD COLUMN job_prefix TEXT NOT NULL DEFAULT 'JOB'")
        print("Added job_prefix column to users.")
    else:
        print("job_prefix column already exists — skipping.")

    # ------------------------------------------------------------------ #
    # 2. Set Joe's prefix (user_id=1)
    # ------------------------------------------------------------------ #
    c.execute("UPDATE users SET job_prefix='JDAMJ' WHERE id=1 AND (job_prefix='JOB' OR job_prefix IS NULL OR job_prefix='')")
    if c.rowcount:
        print("Set job_prefix='JDAMJ' for user_id=1.")

    # ------------------------------------------------------------------ #
    # 3. Print all users so admin can see what needs manual updates
    # ------------------------------------------------------------------ #
    print("\nCurrent users and job prefixes:")
    print(f"  {'ID':<6} {'Username':<24} {'job_prefix':<16}")
    print(f"  {'-'*6} {'-'*24} {'-'*16}")
    for row in c.execute("SELECT id, username, job_prefix FROM users ORDER BY id").fetchall():
        print(f"  {row['id']:<6} {row['username']:<24} {row['job_prefix'] or '(null)':<16}")
    print("\nNOTE: For Verlando/aureum, set job_prefix='ALEJOB' manually after running this script.")
    print("      e.g.: UPDATE users SET job_prefix='ALEJOB' WHERE username='aureum';")

    # ------------------------------------------------------------------ #
    # 4. Create jobs table
    # ------------------------------------------------------------------ #
    c.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id     TEXT NOT NULL UNIQUE,
            user_id    INTEGER NOT NULL REFERENCES users(id),
            job_number TEXT NOT NULL,
            job_title  TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("\nEnsured jobs table exists.")

    # ------------------------------------------------------------------ #
    # 5. Create job_counter table
    # ------------------------------------------------------------------ #
    c.execute("""
        CREATE TABLE IF NOT EXISTS job_counter (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) UNIQUE,
            last_number INTEGER NOT NULL DEFAULT 1110
        )
    """)
    print("Ensured job_counter table exists.")

    conn.commit()

    # ------------------------------------------------------------------ #
    # 6. Backfill jobs table from existing documents
    # ------------------------------------------------------------------ #
    users = c.execute("SELECT id, job_prefix FROM users ORDER BY id").fetchall()
    total_inserted = 0

    for user in users:
        user_id = user['id']
        prefix = user['job_prefix'] or 'JOB'

        # Get distinct job_ids ordered by oldest document first
        job_rows = c.execute("""
            SELECT job_id, MIN(created_at) AS first_created
            FROM documents
            WHERE user_id=? AND job_id IS NOT NULL AND job_id != ''
            GROUP BY job_id
            ORDER BY first_created ASC
        """, (user_id,)).fetchall()

        counter = 0
        inserted = 0
        for jr in job_rows:
            jid = jr['job_id']
            job_number = prefix + str(1111 + counter)
            result = c.execute(
                "INSERT OR IGNORE INTO jobs (job_id, user_id, job_number) VALUES (?, ?, ?)",
                (jid, user_id, job_number),
            )
            if result.rowcount:
                inserted += 1
            counter += 1

        # Upsert job_counter for this user
        c.execute(
            "INSERT OR REPLACE INTO job_counter (user_id, last_number) VALUES (?, ?)",
            (user_id, 1110 + len(job_rows)),
        )

        total_inserted += inserted
        if job_rows:
            print(f"  User {user_id} ({prefix}): {len(job_rows)} job_ids found, {inserted} new jobs inserted, counter set to {1110 + len(job_rows)}")
        else:
            print(f"  User {user_id} ({prefix}): no documents with job_ids found.")

    conn.commit()
    conn.close()

    print(f"\nDone. {total_inserted} new job records inserted total.")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = os.path.join(os.path.dirname(__file__), 'ledger.db')
    run(path)
