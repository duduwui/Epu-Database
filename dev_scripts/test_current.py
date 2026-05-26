import db
subject_id = 2  # Hardcode 2 based on previous test where subject=2
subj = db.execute_query("SELECT name, semester FROM subjects WHERE id = %s", (subject_id,), fetch_one=True)
print("Subject:", subj)

period = db.execute_query("SELECT study_year, semester FROM feedback_forms WHERE cast(semester as text) = %s ORDER BY study_year DESC, created_at DESC LIMIT 1", (str(subj['semester']),), fetch_one=True)
print("Period from forms:", period)

forms = db.execute_query("SELECT id, study_year, semester FROM feedback_forms", fetch_all=True)
print("All forms:", forms)

responses = db.execute_query("SELECT r.id, r.form_id FROM feedback_responses r WHERE r.subject_id = %s", (subject_id,), fetch_all=True)
print("Responses for subj=2:", responses)

