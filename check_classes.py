import db
import sys

try:
    # Check student data
    students = db.execute_query(
        "SELECT s.id, s.user_id, s.class_id, u.username, u.full_name FROM students s JOIN users u ON s.user_id = u.id WHERE u.role='student'", 
        fetch_all=True
    )

    print("\n=== STUDENT CLASS ASSIGNMENTS ===")
    for s in students:
        class_name = "NO CLASS"
        if s['class_id']:
            c = db.execute_query("SELECT name, year, semester FROM classes WHERE id = %s", (s['class_id'],), fetch_one=True)
            if c:
                class_name = f"{c['name']} (Y{c['year']} S{c['semester']})"
        print(f"Student ID {s['id']}: {s['full_name']} ({s['username']}) - Class: {class_name}")

    print("\n=== AVAILABLE CLASSES ===")
    classes = db.execute_query("SELECT id, name, year, semester, section, shift FROM classes ORDER BY year, semester", fetch_all=True)
    if classes:
        for c in classes:
            print(f"Class ID {c['id']}: {c['name']} - Year {c['year']}, Semester {c['semester']}, Section {c['section']}, {c['shift']} shift")
    else:
        print("No classes found!")

finally:
    # Close connection properly
    try:
        db.close_pool()
    except:
        pass
