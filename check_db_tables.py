#!/usr/bin/env python
"""Quick script to check database tables"""
import db  # noqa

conn = db.get_db_connection()
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
rows = cur.fetchall()
cur.close()
conn.close()

print("Database Tables:")
print("=" * 40)
for row in rows:
    print(row[0])
