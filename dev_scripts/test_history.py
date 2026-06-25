import db
import pprint

# find a teacher ID in feedback_responses
res = db.execute_query("SELECT teacher_id, subject_id FROM feedback_responses LIMIT 1", fetch_all=True)
if res:
    teacher_id = res[0]['teacher_id']
    subject_id = res[0]['subject_id']
    
    teacher_user = db.execute_query("SELECT user_id FROM teachers WHERE id = %s", (teacher_id,), fetch_one=True)
    if teacher_user:
        history = db.get_feedback_teacher_history_by_year(teacher_user['user_id'], subject_id)
        for sy, sy_data in history.items():
            for cname, cdata in sy_data['classes'].items():
                print(f"Year {sy}, Cohort {cname}:")
                for st in cdata['students']:
                    print(f"  - {st['student_name']} (Class ID: {st.get('class_id', cdata['class_id'])})")
