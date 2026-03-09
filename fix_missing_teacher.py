#!/usr/bin/env python
"""Fix missing teacher records for users with role='teacher'"""
import db

# Get all users with role 'teacher'
conn = db.get_db_connection()
cur = conn.cursor()
cur.execute("SELECT id, username, full_name FROM users WHERE role = 'teacher'")
teacher_users = cur.fetchall()

print("Teachers in users table:")
print("=" * 60)

for user in teacher_users:
    user_id, username, full_name = user
    
    # Check if teacher record exists
    cur.execute("SELECT id FROM teachers WHERE user_id = %s", (user_id,))
    teacher_record = cur.fetchone()
    
    if teacher_record:
        print(f"✓ {username} ({full_name}) - HAS teacher record")
    else:
        print(f"✗ {username} ({full_name}) - MISSING teacher record - creating...")
        # Create teacher record
        try:
            result = db.create_teacher(user_id)
            print(f"  → Created teacher record with ID: {result}")
        except Exception as e:
            print(f"  → Error: {e}")

cur.close()
conn.close()

print("\n" + "=" * 60)
print("Done! Now refresh the admin/users page to see teachers.")
