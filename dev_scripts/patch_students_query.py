with open('db.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_func = """def get_feedback_teacher_detail_current(teacher_id, subject_id, class_id=None, major_id=None):
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

new_func = """def get_feedback_teacher_detail_current(teacher_id, subject_id, class_id=None, major_id=None):
    \"\"\"Get student details for teacher/subject/class specifically for the currently active period (includes unenrolled)\"\"\"
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
            (SELECT questions FROM feedback_forms WHERE study_year = %s AND cast(semester as text) = cast(%s as text) LIMIT 1) as questions
        FROM students st
        JOIN users u ON st.user_id = u.id
        JOIN student_enrollments se ON st.id = se.student_id
        LEFT JOIN feedback_responses r ON st.id = r.student_id 
             AND r.teacher_id = (SELECT id FROM teachers WHERE user_id = %s)
             AND r.subject_id = %s
             AND r.form_id IN (SELECT id FROM feedback_forms WHERE study_year = %s AND cast(semester as text) = cast(%s as text))
        WHERE se.subject_id = %s
    \"\"\"
    params = [curr_year, str(curr_sem), teacher_id, subject_id, curr_year, str(curr_sem), subject_id]
    
    if class_id:
        query += " AND st.class_id = %s "
        params.append(class_id)
        
    query += " ORDER BY u.full_name ASC "
    
    rows = execute_query(query, tuple(params), fetch_all=True) or []"""

if old_func in text:
    text = text.replace(old_func, new_func)
    with open('db.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Successfully replaced function to include unenrolled active students.")
else:
    print("Could not find the target string to replace.")

