"""Add credits field to subjects table"""
from db import execute_query

sql = """
ALTER TABLE subjects
ADD COLUMN credits INTEGER DEFAULT 6 CHECK (credits > 0 AND credits <= 30);
"""

try:
    execute_query(sql, fetch_all=False)
    print("✓ Migration completed successfully!")
    print("✓ Added credits column to subjects table")
    print("✓ Default credit value: 6")
except Exception as e:
    if "already exists" in str(e) or "duplicate column" in str(e).lower():
        print("✓ Credits column already exists - migration skipped")
    else:
        print(f"✗ Migration failed: {e}")
        raise
