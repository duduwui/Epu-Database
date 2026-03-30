import sys
import os

# Add the project directory to path
sys.path.insert(0, r"c:\Users\DATA FORCE\OneDrive\Pictures\Screenshots\Desktop\MIS")

import db

query = """
    SELECT ep.id, ep.semester, ep.period_type, ep.start_date, ep.end_date, ep.created_by, u.major_id 
    FROM exam_periods ep 
    LEFT JOIN users u ON ep.created_by = u.id;
"""
periods = db.execute_query(query, fetch_all=True)

for p in periods:
    print(p)

# Also check users with 'student' role and their major
query2 = "SELECT id, username, major_id, role FROM users WHERE role = 'student' LIMIT 5"
students = db.execute_query(query2, fetch_all=True)
print("\nStudents:")
for s in students:
    print(s)
