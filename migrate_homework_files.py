"""Add file support to homework table"""
from db import execute_query

sql = """
ALTER TABLE homework
ADD COLUMN filename VARCHAR(255),
ADD COLUMN file_path VARCHAR(500),
ADD COLUMN file_type VARCHAR(50),
ADD COLUMN file_size INTEGER;
"""

try:
    execute_query(sql, fetch_all=False)
    print("✓ Migration completed successfully!")
    print("✓ Added file support columns to homework table")
except Exception as e:
    if "already exists" in str(e) or "duplicate column" in str(e).lower():
        print("✓ Columns already exist - migration skipped")
    else:
        print(f"✗ Migration failed: {e}")
        raise
