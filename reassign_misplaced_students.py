import pg8000.dbapi
from config import config

conn = pg8000.dbapi.connect(
    host=config.DB_HOST,
    port=int(config.DB_PORT),
    database=config.DB_NAME,
    user=config.DB_USER,
    password=config.DB_PASSWORD
)
cur = conn.cursor()

# The 5 misplaced students
student_ids = [73, 79, 80, 81, 82]

print("\n=== REASSIGNING 5 STUDENTS ===\n")

# Show before
print("BEFORE:")
for sid in student_ids:
    cur.execute("""
        SELECT st.id, st.student_number, u.full_name, c.name, c.semester
        FROM students st
        JOIN users u ON st.user_id = u.id
        JOIN classes c ON st.class_id = c.id
        WHERE st.id = %s
    """, (sid,))
    row = cur.fetchone()
    print(f"ID {row[0]}: {row[2]} ({row[1]}) → {row[3]} (Sem {row[4]})")

# Reassign to Class ID 3 (Year 2 - Sem 3 - Section A - Morning)
correct_class_id = 3

print(f"\nReassigning to Class ID {correct_class_id}...\n")

for sid in student_ids:
    cur.execute("""
        UPDATE students 
        SET class_id = %s 
        WHERE id = %s
    """, (correct_class_id, sid))

conn.commit()

# Show after
print("AFTER:")
for sid in student_ids:
    cur.execute("""
        SELECT st.id, st.student_number, u.full_name, c.name, c.semester
        FROM students st
        JOIN users u ON st.user_id = u.id
        JOIN classes c ON st.class_id = c.id
        WHERE st.id = %s
    """, (sid,))
    row = cur.fetchone()
    print(f"ID {row[0]}: {row[2]} ({row[1]}) → {row[3]} (Sem {row[4]}) ✓")

# Verify counts
print("\n=== VERIFICATION ===\n")
cur.execute("""
    SELECT COUNT(*) 
    FROM students st
    JOIN classes c ON st.class_id = c.id
    WHERE st.semester = 3 AND c.semester = 3
""")
count = cur.fetchone()[0]
print(f"Students with semester=3 in semester=3 classes: {count}")

cur.close()
conn.close()

print("\n✅ Done! All 5 students now in correct Sem 3 class.")
