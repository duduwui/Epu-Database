import db

def print_test():
    q = """
    SELECT 
        s.id as student_id,
        u.full_name,
        c.semester,
        s.shift,
        c.name as class_name,
        se.subject_id,
        sub.credits,
        sub.name as subject_name
    FROM students s
    JOIN users u ON s.user_id = u.id
    JOIN classes c ON s.class_id = c.id
    JOIN student_enrollments se ON se.student_id = s.id
    JOIN subjects sub ON se.subject_id = sub.id
    WHERE c.semester = sub.semester
    LIMIT 2
    """
    print(db.execute_query(q, fetch_all=True))
    
    q2 = "SELECT * FROM grade_publishing"
    print(db.execute_query(q2, fetch_all=True))

if __name__ == '__main__':
    print_test()