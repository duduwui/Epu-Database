"""
Test what teachers see - check teacher assignments and subjects
"""
import sys
sys.path.insert(0, '.')
import db

print("=" * 60)
print("Testing Teacher Subject Assignments")
print("=" * 60)

# Get all teachers
teachers = db.execute_query("""
    SELECT t.id, u.full_name as teacher_name
    FROM teachers t
    JOIN users u ON t.user_id = u.id
    ORDER BY u.full_name
""", fetch_all=True)

print(f"\nFound {len(teachers)} teachers\n")

for teacher in teachers:
    print(f"\nTeacher: {teacher['teacher_name']} (ID: {teacher['id']})")
    print("=" * 50)
    
    # Get subjects assigned to this teacher
    subjects = db.get_subjects_by_teacher(teacher['id'])
    
    if subjects:
        print(f"  Assigned to {len(subjects)} subject(s):")
        for subj in subjects:
            print(f"\n  Subject: {subj['name']} (ID: {subj['id']})")
            print(f"    Class: {subj.get('class_name', 'N/A')}")
            print(f"    Year: {subj.get('year', 'N/A')}, Semester: {subj.get('semester', 'N/A')}")
            print(f"    Section: {subj.get('section', 'N/A')}, Shift: {subj.get('shift', 'N/A')}")
            
            # Check enrolled students for this specific subject
            enrolled = db.get_enrolled_students_for_subject(subj['id'])
            if enrolled:
                print(f"    ✓ {len(enrolled)} enrolled student(s):")
                for student in enrolled:
                    print(f"      - {student['full_name']} (ID: {student['id']})")
            else:
                print(f"    ✗ No students enrolled in this subject")
    else:
        print("  No subjects assigned")

print("\n" + "=" * 60)
print("Testing complete!")
