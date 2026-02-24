"""Add publishing control for grades"""
import sys
sys.path.append('.')
import db

try:
    conn = db.get_db_connection()
    if not conn:
        print("✗ Failed to connect to database")
        sys.exit(1)
    
    cur = conn.cursor()
    
    # Read and execute migration
    with open('database/add_grade_publishing.sql', 'r', encoding='utf-8') as f:
        sql = f.read()
        # Split by semicolons and execute each statement separately
        statements = [s.strip() for s in sql.split(';') if s.strip()]
        
        for statement in statements:
            print(f"Executing: {statement[:50]}...")
            cur.execute(statement)
    
    conn.commit()
    print("✓ Migration successful - Added published fields")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"✗ Migration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
