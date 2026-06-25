"""Seed random students across all classes"""
import db
import random
import hashlib

# First ensure all 24 classes exist
print("=== Ensuring all classes exist ===")
semesters_info = [(1,1),(1,2),(2,3),(2,4)]
sections = ['A','B','C']
shifts = ['morning','night']
for year, sem in semesters_info:
    for section in sections:
        for shift in shifts:
            name = 'Year %d - Sem %d - Section %s - %s' % (year, sem, section, shift.title())
            exists = db.execute_query(
                'SELECT id FROM classes WHERE semester = %s AND section = %s AND shift = %s',
                (sem, section, shift), fetch_one=True
            )
            if not exists:
                result = db.execute_query(
                    'INSERT INTO classes (name, year, semester, section, shift) VALUES (%s, %s, %s, %s, %s) RETURNING id',
                    (name, year, sem, section, shift), fetch_one=True
                )
                if result:
                    print(f'  Created: {name}')

first_names = [
    'Ahmad','Sara','Omar','Layla','Hassan','Zahra','Mohammed','Fatima',
    'Ali','Noor','Khalid','Mariam','Yusuf','Dana','Ibrahim','Hana',
    'Rami','Lina','Sami','Reem','Karwan','Shilan','Dara','Zhian',
    'Ari','Bana','Haval','Peri','Soran','Tara','Azad','Guli',
    'Hemin','Naz','Kosar','Rebin','Avan','Dlovan','Chra','Soma'
]
last_names = [
    'Hassan','Ali','Mohammed','Ibrahim','Rashid','Khalil','Ahmed',
    'Mustafa','Salih','Karim','Aziz','Hamid','Faraj','Jamal',
    'Tahir','Bakr','Hasan','Nawzad','Qadir','Jawhar','Zebari',
    'Barwari','Doski','Amedi','Barznji'
]

classes = db.execute_query(
    'SELECT id, semester, section, shift FROM classes ORDER BY semester, section, shift',
    fetch_all=True
)
print(f'\n=== Seeding students across {len(classes)} classes ===')

student_count = 0
for cls in classes:
    cls_id = cls['id']
    sem = cls['semester']
    sec = cls['section']
    shift = cls['shift']

    # Random 3-8 students per class
    n = random.randint(3, 8)
    for i in range(n):
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        full_name = f'{fname} {lname}'
        username = f'{fname.lower()}{lname.lower()}{random.randint(100,9999)}'
        email = f'{username}@student.epu.edu'
        password = hashlib.sha256('student123'.encode()).hexdigest()
        student_num = f'STU{sem}{sec}{random.randint(1000,9999)}'

        # Create user
        user_id = db.execute_query(
            """INSERT INTO users (username, email, password_hash, full_name, role) 
            VALUES (%s, %s, %s, %s, 'student') 
            ON CONFLICT (username) DO NOTHING RETURNING id""",
            (username, email, password, full_name), fetch_one=True
        )
        if user_id:
            # Create student record (no ON CONFLICT, just insert)
            try:
                db.execute_query(
                    'INSERT INTO students (user_id, class_id, student_number) VALUES (%s, %s, %s)',
                    (user_id['id'], cls_id, student_num)
                )
                student_count += 1
            except Exception as e:
                print(f'  Skip duplicate: {e}')

print(f'\nCreated {student_count} students')

# Show distribution
dist = db.execute_query(
    """SELECT c.semester, c.section, c.shift, COUNT(s.id) as cnt
    FROM classes c LEFT JOIN students s ON s.class_id = c.id
    GROUP BY c.semester, c.section, c.shift
    ORDER BY c.semester, c.section, c.shift""",
    fetch_all=True
)
print('\nDistribution:')
for r in dist:
    print(f"  Sem {r['semester']} | {r['section']} | {r['shift']:8s} | {r['cnt']} students")
