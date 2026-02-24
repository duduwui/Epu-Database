"""Run migration through Flask app context"""
from app import app
import db

with app.app_context():
    try:
        print("Connecting to database...")
        conn = db.get_db_connection()
        if not conn:
            print("✗ Failed to connect to database")
            exit(1)
        
        cur = conn.cursor()
        
        print("Adding 'published' column to grades table...")
        cur.execute("ALTER TABLE grades ADD COLUMN IF NOT EXISTS published BOOLEAN DEFAULT FALSE")
        
        print("Adding 'results_published' column to subjects table...")
        cur.execute("ALTER TABLE subjects ADD COLUMN IF NOT EXISTS results_published BOOLEAN DEFAULT FALSE")
        
        print("Updating existing grades to published...")
        cur.execute("UPDATE grades SET published = TRUE WHERE published IS NULL")
        
        print("Creating indexes...")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_grades_published ON grades(published)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_subjects_results_published ON subjects(results_published)")
        
        conn.commit()
        print("\n✓ Migration successful - Added published fields")
        print("✓ Grades table now has 'published' column")
        print("✓ Subjects table now has 'results_published' column")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
