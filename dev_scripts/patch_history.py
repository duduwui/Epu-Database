import sys

with open('db.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_str = '''
    query += " ORDER BY f.study_year DESC, c.semester DESC, c.name ASC, u.full_name ASC"
    
    rows = execute_query(query, tuple(params), fetch_all=True) or []
    
    history = {}
    for r in rows:
        sy = r['study_year'] or 'Unknown Year'
'''

new_str = '''
    query += " ORDER BY f.study_year DESC, c.semester DESC, c.name ASC, u.full_name ASC, r.submitted_at DESC"
    
    rows = execute_query(query, tuple(params), fetch_all=True) or []
    
    history = {}
    seen_responses = set()
    
    for r in rows:
        # Deduplicate student responses per cohort (study_year, class, student)
        c_id = r['class_id']
        st_name = r['student_name']
        sy = r['study_year'] or 'Unknown Year'
        
        uniq_key = (sy, c_id, st_name)
        if uniq_key in seen_responses:
            continue
        seen_responses.add(uniq_key)
        
'''
content = content.replace(old_str, new_str)

with open('db.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched db.py history!")
