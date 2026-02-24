import pg8000.dbapi
from config import config

conn = pg8000.dbapi.connect(
    host=config.DB_HOST,
    port=int(config.DB_PORT),
    database=config.DB_NAME,
    user=config.DB_USER,
    password=config.DB_PASSWORD
)
cur = conn.cursor()

print("\n=== SEMESTER 3 MORNING CLASSES ===\n")
cur.execute("""
    SELECT id, name, semester, shift, section 
    FROM classes 
    WHERE semester = 3 AND shift = 'morning' 
    ORDER BY section
""")
classes = cur.fetchall()

for row in classes:
    class_id, name, sem, shift, section = row
    print(f"Class ID: {class_id}")
    print(f"  Name: {name}")
    print(f"  Section: {section}")
    print()

# Check which section should receive the 5 students
print("\n=== CURRENT CLASS ASSIGNMENTS (Sem 3 Morning) ===\n")
cur.execute("""
    SELECT c.id, c.section, COUNT(st.id) as student_count
    FROM classes c
    LEFT JOIN students st ON st.class_id = c.id
    WHERE c.semester = 3 AND c.shift = 'morning'
    GROUP BY c.id, c.section
    ORDER BY c.section
""")
counts = cur.fetchall()

for row in counts:
    class_id, section, count = row
    print(f"Class ID {class_id} (Section {section}): {count} students")

cur.close()
conn.close()
