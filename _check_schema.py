import db
rows = db.execute_query("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'subjects' ORDER BY ordinal_position", fetch_all=True)
print("=== SUBJECTS TABLE ===")
for r in rows:
    print(r)

# Check a sample subject to see if semester column exists
sample = db.execute_query("SELECT * FROM subjects LIMIT 3", fetch_all=True)
print("\n=== SAMPLE SUBJECTS ===")
for s in sample:
    print(dict(s) if hasattr(s, 'keys') else s)

# Check student_enrollments to see which subjects a student has
# Get a student who was promoted
print("\n=== STUDENT ENROLLMENTS FOR SEM2 STUDENTS ===")
sem2_students = db.execute_query("SELECT s.id, u.full_name, s.semester FROM students s JOIN users u ON s.user_id = u.id WHERE s.semester = 2 LIMIT 3", fetch_all=True)
for stu in sem2_students:
    print(f"\nStudent: {stu['full_name']} (sem {stu['semester']})")
    enrollments = db.execute_query("""
        SELECT se.subject_id, sub.name, sub.semester, sub.credits
        FROM student_enrollments se
        JOIN subjects sub ON se.subject_id = sub.id
        WHERE se.student_id = %s
        ORDER BY sub.semester, sub.name
    """, (stu['id'],), fetch_all=True)
    for e in enrollments:
        print(f"  Subject: {e['name']} (sem {e.get('semester', '?')}, credits {e.get('credits', '?')})")
