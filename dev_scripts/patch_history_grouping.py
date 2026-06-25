import sys

with open("db.py", "r", encoding="utf-8") as f:
    text = f.read()

old_query = """        SELECT 
            f.study_year, f.questions,
            c.id as class_id, c.name as class_name, c.semester as class_semester,"""

new_query = """        SELECT 
            f.study_year, f.questions, f.semester as form_semester,
            c.id as class_id, c.name as class_name, c.semester as class_semester,"""

old_order = """        query += " ORDER BY f.study_year DESC, c.semester DESC, c.name ASC, u.full_name ASC, r.submitted_at DESC\""""

new_order = """        query += " ORDER BY f.study_year DESC, f.semester DESC NULLS LAST, c.semester DESC, c.name ASC, u.full_name ASC, r.submitted_at DESC NULLS LAST\""""

old_loop_start = """    for r in rows:
        # Deduplicate student responses per cohort (study_year, class, student)
        c_id = r['class_id']
        st_name = r['student_name']
        sy = r['study_year'] or 'Unknown Year'
        cn = r['class_name'] or 'Unknown Class'
        
        uniq_key = (sy, c_id, st_name)
        if uniq_key in seen_responses:
            continue
        seen_responses.add(uniq_key)
        c_sem = str(r['class_semester']) if r['class_semester'] else '?'
        c_id = r['class_id']
        cohort_name = f"{cn} (Sem {c_sem})"
        
        if sy not in history:
            history[sy] = {
                'study_year': sy,"""

new_loop_start = """    for r in rows:
        # Deduplicate student responses per cohort (study_year, form_semester, class, student)
        c_id = r['class_id']
        st_name = r['student_name']
        sy = r['study_year'] or 'Unknown Year'
        fs = str(r['form_semester']) if r.get('form_semester') is not None else '?'
        period_key = f"{sy} | Semester {fs}"
        cn = r['class_name'] or 'Unknown Class'
        
        uniq_key = (sy, fs, c_id, st_name)
        if uniq_key in seen_responses:
            continue
        seen_responses.add(uniq_key)
        c_sem = str(r['class_semester']) if r['class_semester'] else '?'
        cohort_name = f"{cn} (Sem {c_sem})"
        
        if period_key not in history:
            history[period_key] = {
                'study_year': period_key,
                'sort_key': f"{sy}-{fs}", """

old_return = """    return sorted(list(history.values()), key=lambda x: x['study_year'], reverse=True)"""

new_return = """    return sorted(list(history.values()), key=lambda x: x['sort_key'], reverse=True)"""

if old_query not in text or old_loop_start not in text or old_return not in text:
    print("Warning: Strings not found")
else:
    text = text.replace(old_query, new_query)
    text = text.replace(old_order, new_order)
    text = text.replace(old_loop_start, new_loop_start)
    text = text.replace(old_return, new_return)
    with open("db.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Patched db.py with new history grouping")
