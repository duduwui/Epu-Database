import db

conn = db.get_db_connection()
cur = conn.cursor()

# Check teachers
cur.execute("SELECT COUNT(*) FROM users WHERE role='teacher'")
teacher_count = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM teachers")
teacher_records = cur.fetchone()[0]

cur.execute("SELECT u.id, u.username, u.full_name FROM users u WHERE u.role='teacher' AND u.id NOT IN (SELECT user_id FROM teachers)")
missing = cur.fetchall()

print(f"Teacher users: {teacher_count}")
print(f"Teacher records: {teacher_records}")
print(f"Missing teacher records: {len(missing)}")

if missing:
    print("\nCreating missing teacher records...")
    for user_id, username, full_name in missing:
        db.create_teacher(user_id)
        print(f"  ✓ Created for {username}")

cur.close()
conn.close()
print("\nDone!")
