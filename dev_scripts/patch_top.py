import re
import sys

with open("db.py", "r", encoding="utf-8") as f:
    text = f.read()

new_func = """
def get_top_students_results(semester=None, class_id=None, shift=None):
    \"\"\"Calculate total published results for all students based on filters.\"\"\"
    query = \"\"\"
        SELECT s.id as student_id, u.full_name as student_name, c.name as class_name, 
               s.shift, c.semester as class_semester, s.class_id
        FROM students s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN classes c ON s.class_id = c.id
        WHERE 1=1
    \"\"\"
    params = []
    if class_id:
        query += " AND s.class_id = %s"
        params.append(class_id)
    if shift:
        query += " AND s.shift = %s"
        params.append(shift)
        
    students = execute_query(query, tuple(params), fetch_all=True) or []
    
    results = []
    for st in students:
        # Get enrolled subjects for the student
        sub_query = \"\"\"
            SELECT sub.id, sub.name, sub.credits, sub.semester
            FROM student_enrollments se
            JOIN subjects sub ON se.subject_id = sub.id
            WHERE se.student_id = %s AND sub.results_published = TRUE
        \"\"\"
        sub_params = [st['student_id']]
        if semester:
            sub_query += " AND sub.semester = %s"
            sub_params.append(semester)
            
        published_subjects = execute_query(sub_query, tuple(sub_params), fetch_all=True) or []
        
        if not published_subjects:
            continue
            
        sem_weighted = 0
        sem_credits_possible = 0
        
        for subj in published_subjects:
            grades_data = get_student_result_grades_for_subject(st['student_id'], subj['id']) or []
            if not grade_rows_have_scores(grades_data):
                continue
                
            total_score, total_max = _calc_grade_totals(grades_data)
            percentage = (total_score / total_max * 100) if total_max > 0 else 0
            
            credits = subj.get('credits') or 0
            weighted_score = round(percentage * credits / 100, 3)
            
            sem_weighted += weighted_score
            sem_credits_possible += credits
            
        if sem_credits_possible > 0:
            results.append({
                'student_id': st['student_id'],
                'student_name': st['student_name'],
                'shift': st['shift'],
                'class_name': st['class_name'],
                'semester': semester if semester else st['class_semester'],
                'total_weighted_score': round(sem_weighted, 3),
                'total_credits': sem_credits_possible
            })
            
    # Sort students by highest total weighted score
    results.sort(key=lambda x: x['total_weighted_score'], reverse=True)
    return results
"""

text += new_func

with open("db.py", "w", encoding="utf-8") as f:
    f.write(text)

print("success")
