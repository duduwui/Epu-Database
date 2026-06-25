import db

def test():
    enrolled = db.execute_query("""
        SELECT s.id, u.full_name, c.semester, c.name as class_name, s.shift 
        FROM students s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN classes c ON s.class_id = c.id
    """, fetch_all=True)
    
    print(len(enrolled))

if __name__ == '__main__':
    test()