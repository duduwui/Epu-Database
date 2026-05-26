import re

with open("db.py", "r", encoding="utf-8") as f:
    text = f.read()

# Replace get_feedback_teacher_history_by_year
import sys

start_idx = text.find("def get_feedback_teacher_history_by_year")
end_idx = text.find("def get_feedback_study_years", start_idx)

if start_idx == -1 or end_idx == -1:
    print("Function boundaries not found.")
    sys.exit(1)

new_func = """def get_feedback_teacher_history_by_year(teacher_id, subject_id, class_id=None):
    \"\"\"Get historical records grouped cleanly strictly by Study Year and Class, including individual student responses\"\"\"
    import json
    
    query = \"\"\"
        SELECT 
            f.study_year, f.questions, f.semester as form_semester,
            c.id as class_id, c.name as class_name, c.semester as class_semester,
            r.ratings, r.comments, r.submitted_at,
            u.full_name as student_name
        FROM feedback_responses r
        JOIN feedback_forms f ON r.form_id = f.id
        LEFT JOIN classes c ON r.snapshot_class_id = c.id
        LEFT JOIN students st ON r.student_id = st.id
        LEFT JOIN users u ON st.user_id = u.id
        WHERE r.teacher_id = (SELECT id FROM teachers WHERE user_id = %s)
          AND r.subject_id = %s
    \"\"\"
    params = [teacher_id, subject_id]
    
    if class_id:
        query += " AND c.id = %s "
        params.append(class_id)
        
    query += " ORDER BY f.study_year DESC, f.semester DESC NULLS LAST, c.semester DESC, c.name ASC, u.full_name ASC, r.submitted_at DESC NULLS LAST"
    
    rows = execute_query(query, tuple(params), fetch_all=True) or []
    
    history = {}
    seen_responses = set()
    
    for r in rows:
        # Deduplicate student responses per cohort (study_year, form_semester, class, student)
        c_id = r['class_id']
        st_name = r['student_name']
        sy = r['study_year'] or 'Unknown Year'
        fs = str(r['form_semester']) if r.get('form_semester') is not None else '?'
        cn = r['class_name'] or 'Unknown Class'
        
        uniq_key = (sy, fs, c_id, st_name)
        if uniq_key in seen_responses:
            continue
        seen_responses.add(uniq_key)
        cohort_name = f"{cn}"
        
        if sy not in history:
            history[sy] = {
                'study_year': sy,
                'total_responses': 0,
                'semesters': {},
                'total_score': 0,
                'total_ratings': 0
            }
            
        grp_yr = history[sy]
        
        if fs not in grp_yr['semesters']:
            grp_yr['semesters'][fs] = {
                'semester': fs,
                'classes': {}
            }
            
        grp_sem = grp_yr['semesters'][fs]
        
        if cohort_name not in grp_sem['classes']:
            grp_sem['classes'][cohort_name] = {
                'cohort_name': cohort_name,
                'class_id': c_id,
                'response_count': 0,
                'class_score': 0,
                'class_rating_cnt': 0,
                'students': []
            }
            
        cls_grp = grp_sem['classes'][cohort_name]
        
        # Parse questions
        q_text_list = []
        if r['questions']:
            q_data = r['questions']
            if type(q_data) == str:
                q_data = json.loads(q_data)
            if isinstance(q_data, list):
                q_text_list = [q.get('text', str(q)) if isinstance(q, dict) else str(q) for q in q_data]
                
        # Parse ratings
        student_score = 0
        student_count = 0
        rtgs = r['ratings']
        answers = []
        
        if rtgs:
            if type(rtgs) == str:
                rtgs = json.loads(rtgs)
            if isinstance(rtgs, dict):
                for idx_str, v in rtgs.items():
                    if str(v).isdigit():
                        answers.append({'index': int(idx_str), 'value': int(v)})
                        student_score += int(v)
                        student_count += 1
            elif isinstance(rtgs, list):
                for idx, v in enumerate(rtgs):
                    if str(v).isdigit():
                        answers.append({'index': idx, 'value': int(v)})
                        student_score += int(v)
                        student_count += 1
                        
        avg_rating = round(student_score / student_count, 2) if student_count > 0 else "N/A"
        
        display_answers = []
        if q_text_list:
            for idx, q_text in enumerate(q_text_list):
                val = next((item['value'] for item in answers if item['index'] == idx), 'N/A')
                display_answers.append({'question': q_text, 'rating': val})
        else:
            for pr in answers:
                display_answers.append({'question': f"Question {pr['index']+1}", 'rating': pr['value']})
                
        cls_grp['students'].append({
            'student_name': r['student_name'] or 'Unknown Student',
            'submitted_at': r['submitted_at'],
            'avg_rating': avg_rating,
            'comments': r['comments'],
            'answers': display_answers
        })
        
        cls_grp['response_count'] += 1
        cls_grp['class_score'] += student_score
        cls_grp['class_rating_cnt'] += student_count
        
        grp_yr['total_score'] += student_score
        grp_yr['total_ratings'] += student_count
        grp_yr['total_responses'] += 1
        
    for grp_yr in history.values():
        grp_yr['overall_avg'] = round(grp_yr['total_score'] / grp_yr['total_ratings'], 2) if grp_yr['total_ratings'] > 0 else "N/A"
        
        sem_list = []
        for sem_info in grp_yr['semesters'].values():
            cls_list = []
            for c in sem_info['classes'].values():
                c['class_avg'] = round(c['class_score'] / c['class_rating_cnt'], 2) if c['class_rating_cnt'] > 0 else "N/A"
                cls_list.append(c)
            sem_info['classes'] = sorted(cls_list, key=lambda x: x['cohort_name'])
            sem_list.append(sem_info)
        grp_yr['semesters'] = sorted(sem_list, key=lambda x: x['semester'])
        
    return sorted(list(history.values()), key=lambda x: x['study_year'], reverse=True)

"""

new_text = text[:start_idx] + new_func + text[end_idx:]

with open("db.py", "w", encoding="utf-8") as f:
    f.write(new_text)

print("success")
