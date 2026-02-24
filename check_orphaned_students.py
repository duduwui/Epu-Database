import db

conn = db.get_db_connection()
cur = conn.cursor()

# Check students without valid user
cur.execute("""
    SELECT COUNT(*) 
    FROM students 
    WHERE user_id IS NULL OR user_id NOT IN (SELECT id FROM users)
""")
students_without_user = cur.fetchone()[0]

# Check students without valid class  
cur.execute("""
    SELECT COUNT(*) 
    FROM students 
    WHERE class_id IS NULL OR class_id NOT IN (SELECT id FROM classes)
""")
students_without_class = cur.fetchone()[0]

# Check total students
cur.execute("SELECT COUNT(*) FROM students")
total_students = cur.fetchone()[0]

# Check students with both valid user and class
cur.execute("""
    SELECT COUNT(*) 
    FROM students st
    JOIN users u ON st.user_id = u.id
    JOIN classes c ON st.class_id = c.id
""")
valid_students = cur.fetchone()[0]

print(f"Total students in DB: {total_students}")
print(f"Students without valid user: {students_without_user}")
print(f"Students without valid class: {students_without_class}")
print(f"Students with valid user AND class (shown in summary): {valid_students}")
print(f"Difference: {total_students - valid_students}")

conn.close()
