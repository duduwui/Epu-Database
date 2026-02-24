import db

conn = db.get_db_connection()
cur = conn.cursor()

try:
    query = """
        SELECT 
            st.id,
            u.full_name,
            st.student_number,
            c.name,
            c.semester,
            c.section,
            c.shift
        FROM students st
        JOIN users u ON st.user_id = u.id
        JOIN classes c ON st.class_id = c.id
    """
    query += " ORDER BY u.full_name"
    
    print("Executing query...")
    cur.execute(query)
    rows = cur.fetchall()
    print(f"SUCCESS! Got {len(rows)} rows")
    
    if rows:
        print(f"First row: {rows[0]}")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    cur.close()
    conn.close()
