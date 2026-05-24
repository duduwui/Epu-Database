def rep():
    with open('db.py', 'r', encoding='utf-8') as f:
        text = f.read()
    import re
    # We will just replace AND (r.form_id IN ... OR (CAST... IS NULL)) with nothing
    text = re.sub(r'AND \(r\.form_id IN \(SELECT id FROM feedback_forms WHERE study_year = %s AND cast\(semester as text\) = cast\(%s as text\)\) \n                  OR \(CAST\(%s as VARCHAR\) IS NULL AND CAST\(%s as VARCHAR\) IS NULL\)\)', '', text)
    # also we need to remove the params
    text = text.replace('params = [curr_year, str(curr_sem) if curr_sem else None, teacher_id, subject_id, curr_year, str(curr_sem) if curr_sem else None, curr_year, curr_sem, subject_id]', 'params = [curr_year, str(curr_sem) if curr_sem else None, teacher_id, subject_id, subject_id]')
    with open('db.py', 'w', encoding='utf-8') as f:
        f.write(text)

rep()
