import db

# Find students who have enrollments
print("=== STUDENTS WITH ENROLLMENTS ===")
rows = db.execute_query("""
    SELECT s.id, u.full_name, s.semester, s.shift, s.section, COUNT(se.id) as enrollment_count
    FROM students s
    JOIN users u ON s.user_id = u.id
    JOIN student_enrollments se ON se.student_id = s.id
    GROUP BY s.id, u.full_name, s.semester, s.shift, s.section
    ORDER BY s.semester, u.full_name
    LIMIT 20
""", fetch_all=True)
for r in rows:
    print(f"  {r['full_name']} - sem {r['semester']}, {r['shift']}/{r['section']}, {r['enrollment_count']} enrollments")

# Now check the specific student who was promoted
# The user said 1 student passed - let's find them
print("\n=== UPGRADE HISTORY ===")
hist = db.execute_query("SELECT * FROM upgrade_history ORDER BY id DESC LIMIT 5", fetch_all=True)
for h in hist:
    print(dict(h))

# Check subjects by semester  
print("\n=== SUBJECTS BY SEMESTER ===")  
for sem in [1,2,3,4]:
    subs = db.execute_query("SELECT id, name, credits FROM subjects WHERE semester = %s ORDER BY name", (sem,), fetch_all=True)
    print(f"\nSemester {sem}: {len(subs)} subjects")
    for s in subs:
        print(f"  {s['name']} (id={s['id']}, credits={s['credits']})")
