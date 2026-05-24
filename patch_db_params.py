with open('db.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# We need to update get_feedback_teacher_detail_current to take class_id
old_func_top = """def get_feedback_teacher_detail_current(teacher_id, subject_id, major_id=None):
    \"\"\"Get student details for teacher/subject specifically for the currently active period\"\"\"
    import json
    
    period = get_latest_feedback_period(major_id)
    curr_year = period.get('study_year')
    curr_sem = period.get('semester')
    
    if not curr_year or not curr_sem:
        return [], []
        
    query = \"\"\"
        SELECT 
            u.full_name as student_name, 
            r.ratings, r.comments, r.submitted_at,
            f.questions
        FROM feedback_responses r
        JOIN feedback_forms f ON r.form_id = f.id
        LEFT JOIN students st ON r.student_id = st.id
        LEFT JOIN users u ON st.user_id = u.id
        WHERE r.teacher_id = (SELECT id FROM teachers WHERE user_id = %s)
          AND r.subject_id = %s
          AND f.study_year = %s
          AND cast(f.semester as text) = cast(%s as text)
        ORDER BY r.submitted_at DESC
    \"\"\"
    rows = execute_query(query, (teacher_id, subject_id, curr_year, str(curr_sem)), fetch_all=True) or []"""

new_func_top = """def get_feedback_teacher_detail_current(teacher_id, subject_id, class_id=None, major_id=None):
    \"\"\"Get student details for teacher/subject/class specifically for the currently active period\"\"\"
    import json
    
    period = get_latest_feedback_period(major_id)
    curr_year = period.get('study_year')
    curr_sem = period.get('semester')
    
    if not curr_year or not curr_sem:
        return [], []
        
    query = \"\"\"
        SELECT 
            u.full_name as student_name, 
            r.ratings, r.comments, r.submitted_at,
            f.questions
        FROM feedback_responses r
        JOIN feedback_forms f ON r.form_id = f.id
        LEFT JOIN students st ON r.student_id = st.id
        LEFT JOIN users u ON st.user_id = u.id
        WHERE r.teacher_id = (SELECT id FROM teachers WHERE user_id = %s)
          AND r.subject_id = %s
          AND f.study_year = %s
          AND cast(f.semester as text) = cast(%s as text)
    \"\"\"
    params = [teacher_id, subject_id, curr_year, str(curr_sem)]
    
    if class_id:
        query += " AND r.snapshot_class_id = %s "
        params.append(class_id)
        
    query += " ORDER BY r.submitted_at DESC "
    
    rows = execute_query(query, tuple(params), fetch_all=True) or []"""

if 'def get_feedback_teacher_detail_current(teacher_id, subject_id, class_id=None' not in text:
    text = text.replace(old_func_top, new_func_top)
    with open('db.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Patched db.py function")

