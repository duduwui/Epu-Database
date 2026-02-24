"""
Migration script to add student enrollments table
"""
import sys
sys.path.insert(0, '.')
import db

def migrate():
    """Add student_enrollments table to track subject enrollment"""
    print("Adding student_enrollments table...")
    
    # Read SQL migration file
    with open('database/add_student_enrollments.sql', 'r') as f:
        sql = f.read()
    
    # Execute migration
    try:
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        print("✓ Successfully added student_enrollments table")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Student Enrollments Migration")
    print("=" * 60)
    migrate()
    print("=" * 60)
    print("Migration complete!")
