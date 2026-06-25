import re

with open("db.py", "r", encoding="utf-8") as f:
    text = f.read()

new_func = """
def get_teacher_unique_student_count(teacher_id):
    \"\"\"Get the number of unique students taught by a teacher across all subjects & classes.\"\"\"
    query = \"\"\"
        SELECT COUNT(DISTINCT st.id) AS unique_students
        FROM teacher_assignments ta
        JOIN student_enrollments se ON se.subject_id = ta.subject_id
        JOIN students st ON st.id = se.student_id AND st.class_id = ta.class_id
        WHERE ta.teacher_id = %s
    \"\"\"
    res = execute_query(query, (teacher_id,), fetch_one=True)
    return res['unique_students'] if res else 0

"""

# Let's insert it before get_teacher_dashboard_groups
insertion_point = text.find("def get_teacher_dashboard_groups")
text = text[:insertion_point] + new_func + text[insertion_point:]

with open("db.py", "w", encoding="utf-8") as f:
    f.write(text)
print("success")
