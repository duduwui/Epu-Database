"""Test credits field"""
from db import execute_query

# Check current credits for English subjects
subjects = execute_query(
    "SELECT id, name, credits, semester FROM subjects WHERE name ILIKE %s", 
    ('%english%',), 
    fetch_all=True
)

print(f'\nFound {len(subjects)} subjects with "english" in name:')
for s in subjects:
    print(f'  ID: {s["id"]}, Name: {s["name"]}, Credits: {s.get("credits", "NULL")}, Semester: {s["semester"]}')

# Check all subjects
all_subjects = execute_query("SELECT id, name, credits, semester FROM subjects ORDER BY semester, name", fetch_all=True)
print(f'\nAll subjects ({len(all_subjects)} total):')
for s in all_subjects:
    print(f'  Sem {s["semester"]}: {s["name"]} - {s.get("credits", "NULL")} credits')
