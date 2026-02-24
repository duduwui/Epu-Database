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

print("\n=== CHECKING SEMESTER MISMATCH ===\n")

# Students with semester=3 in students table
cur.execute("SELECT COUNT(*) FROM students WHERE semester = 3")
total_sem3_students = cur.fetchone()[0]
print(f"Total students with semester=3 in students table: {total_sem3_students}")

# Students with semester=3, joined to their CLASS semester
cur.execute("""
    SELECT 
        st.id,
        st.student_number,
        u.full_name,
        st.semester as student_semester,
        c.semester as class_semester,
        c.name as class_name
    FROM students st
    JOIN users u ON st.user_id = u.id
    JOIN classes c ON st.class_id = c.id
    WHERE st.semester = 3
    ORDER BY st.id
""")
students_with_classes = cur.fetchall()
print(f"Students with semester=3 that have valid user+class: {len(students_with_classes)}")

# Check for mismatches
mismatches = []
for row in students_with_classes:
    student_id, student_num, name, student_sem, class_sem, class_name = row
    if student_sem != class_sem:
        mismatches.append(row)

print(f"\n❌ MISMATCHES FOUND: {len(mismatches)} students")
print(f"These students have semester=3 but their CLASS has a different semester:\n")

if mismatches:
    for row in mismatches:
        student_id, student_num, name, student_sem, class_sem, class_name = row
        print(f"Student ID: {student_id}")
        print(f"  Name: {name}")
        print(f"  Number: {student_num}")
        print(f"  Student Semester: {student_sem}")
        print(f"  Class Semester: {class_sem} ❌")
        print(f"  Class Name: {class_name}")
        print()

# Now check what the attendance summary query returns
print("\n=== WHAT ATTENDANCE SUMMARY SEES ===")
cur.execute("""
    SELECT COUNT(*)
    FROM students st
    JOIN users u ON st.user_id = u.id
    JOIN classes c ON st.class_id = c.id
    WHERE c.semester = 3
""")
summary_count = cur.fetchone()[0]
print(f"Attendance summary query (filters by c.semester = 3): {summary_count} students")

cur.close()
conn.close()

print(f"\n📊 SUMMARY:")
print(f"Dashboard shows: {total_sem3_students} (counts students.semester = 3)")
print(f"Attendance summary shows: {summary_count} (filters by classes.semester = 3)")
print(f"Difference: {total_sem3_students - summary_count} students in wrong classes")
