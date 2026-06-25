import db
import json

def debug():
    print("--- GRADE COMPONENTS ---")
    comps = db.execute_query("SELECT * FROM grade_components ORDER BY subject_id", fetch_all=True)
    for c in comps:
        print(f"ID: {c['id']}, Subject: {c['subject_id']}, Type: '{c['component_type']}', Name: '{c['component_name']}', Pair: {c['pair_group']}, Max: {c['max_score']}")

    print("\n--- STUDENTS ---")
    students = db.execute_query("""
        SELECT s.id, u.full_name, s.class_id, s.year, s.semester, s.section, s.shift 
        FROM students s JOIN users u ON s.user_id = u.id
    """, fetch_all=True)
    for s in students:
        print(f"ID: {s['id']}, Name: {s['full_name']}, ClassID: {s['class_id']}, Sem: {s['semester']}, Sect: {s['section']}")

    print("\n--- CLASSES ---")
    classes = db.execute_query("SELECT * FROM classes", fetch_all=True)
    for c in classes:
        print(f"ID: {c['id']}, Name: {c['name']}, Sem: {c['semester']}, Sect: {c['section']}")

    print("\n--- ENROLLMENTS ---")
    enrolls = db.execute_query("SELECT * FROM student_enrollments LIMIT 20", fetch_all=True)
    for e in enrolls:
        print(e)

if __name__ == "__main__":
    debug()
