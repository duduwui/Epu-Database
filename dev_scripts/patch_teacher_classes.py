import sys

with open("db.py", "r", encoding="utf-8") as f:
    text = f.read()

old_string = """    query = '''
        SELECT DISTINCT c.id as class_id, c.name as class_name
        FROM feedback_responses r
        JOIN classes c ON r.snapshot_class_id = c.id
        JOIN feedback_forms f ON r.form_id = f.id
        WHERE r.teacher_id = (SELECT id FROM teachers WHERE user_id = %s)
          AND r.subject_id = %s
          AND f.study_year = %s
          AND cast(f.semester as text) = cast(%s as text)
        ORDER BY c.name
    '''
    
    return execute_query(query, (teacher_id, subject_id, curr_year, str(curr_sem)), fetch_all=True) or []"""

new_string = """    query = '''
        SELECT class_id, class_name FROM (
            SELECT c.id as class_id, c.name as class_name
            FROM feedback_responses r
            JOIN classes c ON r.snapshot_class_id = c.id
            JOIN feedback_forms f ON r.form_id = f.id
            WHERE r.teacher_id = (SELECT id FROM teachers WHERE user_id = %s)
              AND r.subject_id = %s
              AND f.study_year = %s
              AND cast(f.semester as text) = cast(%s as text)
            UNION
            SELECT c.id as class_id, c.name as class_name
            FROM student_enrollments se
            JOIN students st ON se.student_id = st.id
            JOIN classes c ON st.class_id = c.id
            WHERE se.subject_id = %s
        ) as combined
        ORDER BY class_name
    '''
    
    return execute_query(query, (teacher_id, subject_id, curr_year, str(curr_sem), subject_id), fetch_all=True) or []"""

if old_string not in text:
    print("Warning: old_string not found")
else:
    text = text.replace(old_string, new_string)
    with open("db.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Patched get_feedback_teacher_classes")
