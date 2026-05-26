import db
import json
res = db.execute_query("SELECT teacher_id, subject_id FROM feedback_responses LIMIT 1", fetch_all=True)
teacher_id = res[0]['teacher_id']
subject_id = res[0]['subject_id']
teacher_user = db.execute_query("SELECT user_id FROM teachers WHERE id = %s", (teacher_id,), fetch_one=True)
history_list = db.get_feedback_teacher_history_by_year(teacher_user['user_id'], subject_id)

for sy_data in history_list:
    sy = sy_data['study_year']
    for cdata in sy_data['classes']:
        print(f"Cohort {cdata['cohort_name']}:")
        for st in cdata['students']:
            print(f"  - {st['student_name']} {st['avg_rating']}")
