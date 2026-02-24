"""
Test enrollment query - check if students are enrolled in subjects
"""
import sys
sys.path.insert(0, '.')
import db

print("=" * 60)
print("Testing Student Enrollment Queries")
print("=" * 60)

# Test 1: Get all enrollments
print("\n1. All student enrollments:")
enrollments = db.execute_query("""
    SELECT se.id, se.student_id, se.subject_id, 
           s.full_name as student_name, 
           sub.name as subject_name
    FROM student_enrollments se
    JOIN students st ON se.student_id = st.id
    JOIN users s ON st.user_id = s.id
    JOIN subjects sub ON se.subject_id = sub.id
    ORDER BY se.id
""", fetch_all=True)

if enrollments:
    for e in enrollments:
        print(f"  Enrollment ID: {e['id']}")
        print(f"    Student: {e['student_name']} (ID: {e['student_id']})")
        print(f"    Subject: {e['subject_name']} (ID: {e['subject_id']})")
        print()
else:
    print("  No enrollments found!")

# Test 2: Check all subjects
print("\n2. All subjects:")
subjects = db.execute_query("SELECT id, name, semester FROM subjects ORDER BY semester, name", fetch_all=True)
for s in subjects:
    print(f"  Subject ID {s['id']}: {s['name']} (Semester {s['semester']})")
    
    # Try getting enrolled students for each subject
    enrolled = db.get_enrolled_students_for_subject(s['id'])
    if enrolled:
        print(f"    ✓ {len(enrolled)} student(s) enrolled:")
        for student in enrolled:
            print(f"      - {student['full_name']}")
    else:
        print(f"    ✗ No students enrolled")

# Test 3: Check students and their classes
print("\n3. All students with their classes:")
students = db.execute_query("""
    SELECT s.id, u.full_name, c.name as class_name, c.semester, c.section, c.shift
    FROM students s
    JOIN users u ON s.user_id = u.id
    LEFT JOIN classes c ON s.class_id = c.id
    ORDER BY u.full_name
""", fetch_all=True)

for s in students:
    print(f"  Student ID {s['id']}: {s['full_name']}")
    if s['class_name']:
        print(f"    Class: {s['class_name']} (Semester {s['semester']}, Section {s['section']}, {s['shift']} shift)")
    else:
        print(f"    No class assigned")

print("\n" + "=" * 60)
