import pg8000.dbapi
from config import config

# Database connection
conn = pg8000.dbapi.connect(
    host=config.DB_HOST,
    port=int(config.DB_PORT),
    database=config.DB_NAME,
    user=config.DB_USER,
    password=config.DB_PASSWORD
)
cur = conn.cursor()

print("\n=== ALL Semester 3 Students (Dashboard Count) ===")
cur.execute("""
    SELECT id, student_number, semester, shift, user_id, class_id
    FROM students
    WHERE semester = 3
    ORDER BY id
""")
all_students = cur.fetchall()
print(f"Total: {len(all_students)} students")
for row in all_students:
    print(f"ID: {row[0]}, Number: {row[1]}, Sem: {row[2]}, Shift: {row[3]}, UserID: {row[4]}, ClassID: {row[5]}")

print("\n=== Semester 3 Students WITH Valid User and Class (Summary Count) ===")
cur.execute("""
    SELECT 
        st.id,
        st.student_number,
        st.semester,
        st.shift,
        st.user_id,
        st.class_id,
        u.full_name,
        c.name
    FROM students st
    JOIN users u ON st.user_id = u.id
    JOIN classes c ON st.class_id = c.id
    WHERE st.semester = 3
    ORDER BY st.id
""")
valid_students = cur.fetchall()
print(f"Total: {len(valid_students)} students")
for row in valid_students:
    print(f"ID: {row[0]}, Number: {row[1]}, Sem: {row[2]}, Shift: {row[3]}, User: {row[6]}, Class: {row[7]}")

print("\n=== MISSING Students (Dashboard shows but Summary doesn't) ===")
all_ids = {row[0] for row in all_students}
valid_ids = {row[0] for row in valid_students}
missing_ids = all_ids - valid_ids

if missing_ids:
    print(f"Found {len(missing_ids)} students without valid user or class:")
    for student in all_students:
        if student[0] in missing_ids:
            student_id, student_number, sem, shift, user_id, class_id = student
            print(f"\nStudent ID: {student_id}, Number: {student_number}")
            print(f"  Semester: {sem}, Shift: {shift}")
            print(f"  User ID: {user_id} (valid: {user_id is not None})")
            print(f"  Class ID: {class_id} (valid: {class_id is not None})")
            
            # Check if user exists
            if user_id:
                cur.execute("SELECT id, username, full_name FROM users WHERE id = %s", (user_id,))
                user = cur.fetchone()
                if user:
                    print(f"  User EXISTS: {user[2]} ({user[1]})")
                else:
                    print(f"  User DOES NOT EXIST (orphaned user_id)")
            else:
                print(f"  No user_id assigned")
            
            # Check if class exists
            if class_id:
                cur.execute("SELECT id, name, semester, shift FROM classes WHERE id = %s", (class_id,))
                cls = cur.fetchone()
                if cls:
                    print(f"  Class EXISTS: {cls[1]} (Sem {cls[2]}, {cls[3]})")
                else:
                    print(f"  Class DOES NOT EXIST (orphaned class_id)")
            else:
                print(f"  No class_id assigned")
else:
    print("No missing students - counts should match!")

cur.close()
conn.close()
