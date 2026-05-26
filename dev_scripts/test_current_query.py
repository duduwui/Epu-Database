import db

class_id = 1
subject_id = 2
teacher_id = 1
major_id = 1

# Let's verify what happens when get_feedback_teacher_detail_current fetches
resp = db.get_feedback_teacher_detail_current(teacher_id, subject_id, class_id, major_id)
print(f"Students count: {len(resp[0])}")
for student in resp[0]:
    print(student['student_name'], student['avg_rating'])

