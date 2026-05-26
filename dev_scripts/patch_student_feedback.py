import sys

with open("blueprints/student.py", "r", encoding="utf-8") as f:
    text = f.read()

old_query = """            db.execute_query('''
                INSERT INTO feedback_responses (form_id, student_id, teacher_id, subject_id, ratings, comments)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (form_id, student['id'], tch_id, sub_id, json.dumps(ratings), comments))"""

new_query = """            db.execute_query('''
                INSERT INTO feedback_responses (form_id, student_id, teacher_id, subject_id, ratings, comments, snapshot_class_id)
                VALUES (%s, %s, %s, %s, %s, %s, (SELECT class_id FROM students WHERE id = %s))
            ''', (form_id, student['id'], tch_id, sub_id, json.dumps(ratings), comments, student['id']))"""

if old_query not in text:
    print("Warning: old_string not found")
else:
    text = text.replace(old_query, new_query)
    with open("blueprints/student.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Patched student.py for snapshot_class_id")
