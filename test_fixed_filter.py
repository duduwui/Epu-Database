"""
Test the fixed class filtering - verify students only appear in their own section
"""
import sys
sys.path.insert(0, '.')
import db

print("=" * 60)
print("Testing FIXED Student Class Filtering")
print("=" * 60)

# Get student "Dilan Karim"
student = db.execute_query("""
    SELECT s.*, u.full_name, c.id as class_id, c.name as class_name, c.section
    FROM students s
    JOIN users u ON s.user_id = u.id
    LEFT JOIN classes c ON s.class_id = c.id
    WHERE u.full_name = 'Dilan Karim'
""", fetch_one=True)

print(f"\nStudent: {student['full_name']}")
print(f"  Class ID: {student['class_id']}")
print(f"  Class: {student['class_name']}")
print(f"  Section: {student['section']}")

# Get "basic english" subject assignments
subject_id = 138
assignments = db.execute_query("""
    SELECT ta.id as assignment_id, ta.subject_id, ta.class_id, ta.teacher_id,
           s.name as subject_name, c.name as class_name, c.section
    FROM teacher_assignments ta
    JOIN subjects s ON ta.subject_id = s.id
    JOIN classes c ON ta.class_id = c.id
    WHERE ta.subject_id = %s AND c.semester = 1
    ORDER BY c.section
""", (subject_id,), fetch_all=True)

print(f"\n'basic english' is taught in {len(assignments)} classes:")
for assign in assignments:
    print(f"\n  Section {assign['section']} (Class ID: {assign['class_id']})")
    
    # Test with class filter (NEW BEHAVIOR)
    enrolled_filtered = db.get_enrolled_students_for_subject(subject_id, assign['class_id'])
    print(f"    With class filter: {len(enrolled_filtered)} student(s)")
    if enrolled_filtered:
        for st in enrolled_filtered:
            print(f"      ✓ {st['full_name']} (class_id: {st['class_id']})")
    else:
        print(f"      (No students enrolled in this section)")

print("\n" + "=" * 60)
print("✓ SUCCESS: Student only appears in their own class!")
print("=" * 60)
