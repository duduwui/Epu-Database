"""
Debug script - simulate what teacher sees when they click add grades
"""
import sys
sys.path.insert(0, '.')
import db

print("=" * 60)
print("Simulating Teacher Add Grades Page")
print("=" * 60)

# Simulate teacher "Prof. Mohammed Kareem" (ID: 9) viewing basic english for Sem 1 Section A Morning
teacher_id = 9
teacher = db.execute_query("SELECT t.*, u.full_name FROM teachers t JOIN users u ON t.user_id = u.id WHERE t.id = %s", (teacher_id,), fetch_one=True)

print(f"\nTeacher: {teacher['full_name']} (ID: {teacher_id})")

# Get subjects for this teacher
subjects = db.get_subjects_by_teacher(teacher_id)
print(f"\nTotal subjects assigned: {len(subjects)}")

# Find first Sem 1 Section A Morning subject
target_subject = None
for s in subjects:
    if (s.get('semester') == 1 and 
        s.get('section') == 'A' and 
        s.get('shift') == 'morning' and
        s['name'] == 'basic english'):
        target_subject = s
        break

if target_subject:
    print(f"\nTarget Subject: {target_subject['name']} (ID: {target_subject['id']})")
    print(f"  Class: {target_subject.get('class_name')}")
    print(f"  Year: {target_subject.get('year')}, Semester: {target_subject.get('semester')}")
    print(f"  Section: {target_subject.get('section')}, Shift: {target_subject.get('shift')}")
    
    # This is what the route does:
    print(f"\n--- Calling get_enrolled_students_for_subject({target_subject['id']}) ---")
    students = db.get_enrolled_students_for_subject(target_subject['id'])
    
    print(f"\nReturned {len(students) if students else 0} students:")
    if students:
        for student in students:
            print(f"\n  Student ID: {student['id']}")
            print(f"    Name: {student['full_name']}")
            print(f"    Username: {student.get('username')}")
            print(f"    Email: {student.get('email')}")
            print(f"    Class: {student.get('class_name')}")
            print(f"    Enrolled At: {student.get('enrolled_at')}")
    else:
        print("  ✗ NO STUDENTS RETURNED!")
        
    # Check grade components
    print(f"\n--- Checking Grade Components ---")
    components = db.get_grade_components_by_subject(target_subject['id'])
    if components:
        print(f"  ✓ {len(components)} component(s) defined")
        for comp in components:
            print(f"    - {comp.get('component_name')} ({comp.get('component_type')})")
    else:
        print(f"  ✗ No grade components defined for this subject!")
        
else:
    print("\n✗ Could not find basic english Sem 1 Section A Morning!")

print("\n" + "=" * 60)
