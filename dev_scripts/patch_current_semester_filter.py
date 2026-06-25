import sys

with open("db.py", "r", encoding="utf-8") as f:
    text = f.read()

old_string = """        WHERE se.subject_id = %s
    \"\"\"
    params = [curr_year, str(curr_sem) if curr_sem else None, teacher_id, subject_id, curr_year, str(curr_sem) if curr_sem else None, subject_id]"""

new_string = """        WHERE se.subject_id = %s AND cast(st.semester as text) = cast(%s as text)
    \"\"\"
    params = [curr_year, str(curr_sem) if curr_sem else None, teacher_id, subject_id, curr_year, str(curr_sem) if curr_sem else None, subject_id, subj_sem]"""

if old_string not in text:
    print("Warning: old_string not found")
else:
    text = text.replace(old_string, new_string)
    with open("db.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Patched db.py with st.semester filter")
