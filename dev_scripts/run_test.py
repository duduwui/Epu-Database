import sys
sys.path.insert(0, "c:/Users/DATA FORCE/OneDrive/Pictures/Screenshots/Desktop/MIS")
import db
import json
from datetime import datetime

print("CURRENT TIME GENERATED:", datetime.now())

query = '''
    SELECT ep.id, ep.semester, ep.period_type, ep.start_date, ep.end_date, ep.created_by, u.major_id 
    FROM exam_periods ep 
    LEFT JOIN users u ON ep.created_by = u.id;
'''
periods = db.execute_query(query, fetch_all=True)

print("EXAM PERIODS in DB (All Majors):")
for p in periods:
    print(dict(p))

student = db.execute_query("SELECT id, username, major_id, role FROM users WHERE role = 'student' LIMIT 3;", fetch_all=True)
print("\nSTUDENT PROFILES:")
for s in student:
    print(dict(s))
