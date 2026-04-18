#!/usr/bin/env python3
"""
Migration: add result_description, eval_brief, judgement to tasks table.
Safe for existing rows — new columns get default empty string.
Run once. Idempotent (checks if columns exist first).
"""
import sys
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "relay.db"

COLUMNS = ["result_description", "eval_brief", "judgement"]

def migrate():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH} — skipping migration (will be created on first run)")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Get existing columns
    cursor.execute("PRAGMA table_info(tasks)")
    existing = {row[1] for row in cursor.fetchall()}

    added = []
    for col in COLUMNS:
        if col not in existing:
            cursor.execute(f"ALTER TABLE tasks ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")
            added.append(col)
            print(f"  + added {col}")
        else:
            print(f"  = {col} already exists, skipping")

    conn.commit()
    conn.close()

    if added:
        print(f"Migration complete — added: {', '.join(added)}")
    else:
        print("No migration needed — all columns already present")


if __name__ == "__main__":
    migrate()