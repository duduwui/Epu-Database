import db
rows = db.execute_query("""
    SELECT se.subject_id, sub.name, sub.semester, sub.credits
    FROM student_enrollments se
    JOIN subjects sub ON se.subject_id = sub.id
    WHERE se.student_id = (SELECT s.id FROM students s JOIN users u ON s.user_id = u.id WHERE u.full_name = 'Yusuf Tariq')
    ORDER BY sub.semester, sub.name
""", fetch_all=True)
for r in rows:
    print(f"  Sem {r['semester']}: {r['name']} (id={r['subject_id']}, credits={r['credits']})")
