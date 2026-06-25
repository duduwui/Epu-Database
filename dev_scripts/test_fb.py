import db
res = db.execute_query("SELECT r.*, u.full_name FROM feedback_responses r JOIN students st ON r.student_id = st.id JOIN users u ON st.user_id = u.id WHERE u.full_name ILIKE '%mansour%'", fetch_all=True)
for r in res: print(r)
