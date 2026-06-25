with open('db.py', 'r', encoding='utf-8') as f:
    text = f.read()

new_func = """
def get_feedback_teacher_classes(teacher_id, subject_id, major_id=None):
    period = get_latest_feedback_period(major_id)
    curr_year = period.get('study_year')
    curr_sem = period.get('semester')

    query = '''
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
    
    return execute_query(query, (teacher_id, subject_id, curr_year, str(curr_sem)), fetch_all=True) or []
"""

if 'def get_feedback_teacher_classes' not in text:
    text = text.replace('def get_feedback_teacher_detail_current', new_func + '\ndef get_feedback_teacher_detail_current')
    with open('db.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print('Added get_feedback_teacher_classes to db.py')
