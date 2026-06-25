"""
Insert Sample Data for MIS System
This script populates the database with realistic sample data
"""

import psycopg2
from werkzeug.security import generate_password_hash
from datetime import date, timedelta
import random

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'mis_system',
    'user': 'postgres',
    'password': '0998'
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def insert_sample_data():
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # =============================================
        # 1. CREATE TEACHERS
        # =============================================
        print("Creating teachers...")
        teachers_data = [
            ('teacher1', 'Dr. Ahmad Hassan', 'ahmad.hassan@epu.edu', 'MIS Department', '0770-123-4567'),
            ('teacher2', 'Dr. Sara Ali', 'sara.ali@epu.edu', 'MIS Department', '0770-234-5678'),
            ('teacher3', 'Prof. Mohammed Kareem', 'mohammed.kareem@epu.edu', 'MIS Department', '0770-345-6789'),
            ('teacher4', 'Dr. Layla Ibrahim', 'layla.ibrahim@epu.edu', 'MIS Department', '0770-456-7890'),
            ('teacher5', 'Dr. Omar Rashid', 'omar.rashid@epu.edu', 'MIS Department', '0770-567-8901'),
        ]
        
        teacher_ids = []
        for username, full_name, email, dept, phone in teachers_data:
            # Create user account
            cur.execute("""
                INSERT INTO users (username, password_hash, full_name, email, role)
                VALUES (%s, %s, %s, %s, 'teacher')
                ON CONFLICT (username) DO UPDATE SET full_name = EXCLUDED.full_name
                RETURNING id
            """, (username, generate_password_hash('teacher123'), full_name, email))
            user_id = cur.fetchone()[0]
            
            # Create teacher profile
            cur.execute("""
                INSERT INTO teachers (user_id, department, phone)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET department = EXCLUDED.department
                RETURNING id
            """, (user_id, dept, phone))
            teacher_ids.append(cur.fetchone()[0])
        
        print(f"  Created {len(teacher_ids)} teachers")
        
        # =============================================
        # 2. GET SEMESTERS (Classes)
        # =============================================
        cur.execute("SELECT id, name, year FROM classes ORDER BY year, id")
        semesters = cur.fetchall()
        semester_dict = {s[1]: s[0] for s in semesters}
        print(f"  Found {len(semesters)} semesters")
        
        # =============================================
        # 3. CREATE SUBJECTS (5 per semester)
        # =============================================
        print("Creating subjects...")
        subjects_data = {
            'Year 1 - Semester 1': [
                ('Introduction to MIS', 'Fundamentals of Management Information Systems'),
                ('Computer Fundamentals', 'Basic computer concepts and applications'),
                ('Business Mathematics', 'Mathematical concepts for business'),
                ('English for Business', 'Business communication skills'),
                ('Principles of Management', 'Introduction to management theories'),
            ],
            'Year 1 - Semester 2': [
                ('Database Management', 'Introduction to databases and SQL'),
                ('Programming Fundamentals', 'Basic programming concepts'),
                ('Business Statistics', 'Statistical analysis for business'),
                ('Accounting Principles', 'Fundamentals of accounting'),
                ('Organizational Behavior', 'Understanding human behavior in organizations'),
            ],
            'Year 2 - Semester 3': [
                ('Systems Analysis & Design', 'Analyzing and designing information systems'),
                ('Web Development', 'Creating web applications'),
                ('Data Analytics', 'Analyzing business data'),
                ('E-Commerce', 'Electronic commerce concepts'),
                ('Project Management', 'Managing IT projects'),
            ],
            'Year 2 - Semester 4': [
                ('Information Security', 'Protecting information assets'),
                ('Enterprise Systems', 'ERP and enterprise applications'),
                ('Business Intelligence', 'BI tools and techniques'),
                ('IT Strategy', 'Strategic use of information technology'),
                ('Capstone Project', 'Final year project'),
            ],
        }
        
        subject_ids = []
        teacher_index = 0
        for semester_name, subjects in subjects_data.items():
            if semester_name in semester_dict:
                class_id = semester_dict[semester_name]
                for subject_name, description in subjects:
                    teacher_id = teacher_ids[teacher_index % len(teacher_ids)]
                    teacher_index += 1
                    
                    cur.execute("""
                        INSERT INTO subjects (name, class_id, teacher_id, description)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        RETURNING id
                    """, (subject_name, class_id, teacher_id, description))
                    result = cur.fetchone()
                    if result:
                        subject_ids.append(result[0])
        
        # Get all subject IDs
        cur.execute("SELECT id, name, class_id, teacher_id FROM subjects")
        all_subjects = cur.fetchall()
        print(f"  Created/Found {len(all_subjects)} subjects")
        
        # =============================================
        # 4. CREATE STUDENTS (10 per semester = 40 total)
        # =============================================
        print("Creating students...")
        
        first_names = ['Ali', 'Ahmed', 'Mohammed', 'Hassan', 'Omar', 'Yusuf', 'Ibrahim', 'Khalid', 
                       'Sara', 'Fatima', 'Zainab', 'Mariam', 'Noor', 'Layla', 'Hana', 'Rania']
        last_names = ['Hassan', 'Ali', 'Mohammed', 'Ahmad', 'Kareem', 'Rashid', 'Ibrahim', 'Salim',
                      'Jamal', 'Nasser', 'Farid', 'Hamid', 'Saeed', 'Majid', 'Walid', 'Tariq']
        
        student_count = 0
        for semester in semesters:
            class_id, class_name, year = semester
            
            for i in range(10):  # 10 students per semester
                student_num = f"MIS{year}0{class_id}{i+1:02d}"
                first = random.choice(first_names)
                last = random.choice(last_names)
                full_name = f"{first} {last}"
                username = f"student{class_id}_{i+1}"
                email = f"{first.lower()}.{last.lower()}{random.randint(1,99)}@student.epu.edu"
                phone = f"075{random.randint(0,9)}-{random.randint(100,999)}-{random.randint(1000,9999)}"
                
                # Create user account
                cur.execute("""
                    INSERT INTO users (username, password_hash, full_name, email, role)
                    VALUES (%s, %s, %s, %s, 'student')
                    ON CONFLICT (username) DO UPDATE SET full_name = EXCLUDED.full_name
                    RETURNING id
                """, (username, generate_password_hash('student123'), full_name, email))
                user_id = cur.fetchone()[0]
                
                # Create student profile
                cur.execute("""
                    INSERT INTO students (user_id, student_number, class_id, phone)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET class_id = EXCLUDED.class_id
                """, (user_id, student_num, class_id, phone))
                student_count += 1
        
        print(f"  Created {student_count} students")
        
        # =============================================
        # 5. GET ALL STUDENTS FOR GRADES/ATTENDANCE
        # =============================================
        cur.execute("""
            SELECT s.id, s.user_id, s.class_id, u.full_name 
            FROM students s 
            JOIN users u ON s.user_id = u.id
        """)
        all_students = cur.fetchall()
        
        # Group students by class
        students_by_class = {}
        for student in all_students:
            class_id = student[2]
            if class_id not in students_by_class:
                students_by_class[class_id] = []
            students_by_class[class_id].append(student)
        
        # =============================================
        # 6. CREATE ATTENDANCE RECORDS
        # =============================================
        print("Creating attendance records...")
        
        attendance_count = 0
        today = date.today()
        statuses = ['present', 'present', 'present', 'present', 'absent', 'late', 'excused']  # Weighted towards present
        
        for subject in all_subjects:
            subject_id, subject_name, class_id, teacher_id = subject
            
            if class_id in students_by_class:
                # Create attendance for last 10 class days
                for day_offset in range(10):
                    attendance_date = today - timedelta(days=day_offset * 2 + 1)  # Every other day
                    if attendance_date.weekday() < 5:  # Only weekdays
                        for student in students_by_class[class_id]:
                            student_id = student[0]
                            status = random.choice(statuses)
                            
                            cur.execute("""
                                INSERT INTO attendance (student_id, subject_id, date, status)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """, (student_id, subject_id, attendance_date, status))
                            attendance_count += 1
        
        print(f"  Created {attendance_count} attendance records")
        
        # =============================================
        # 7. CREATE GRADES
        # =============================================
        print("Creating grades...")
        
        grade_types = [
            ('quiz', 'Quiz 1', 20),
            ('quiz', 'Quiz 2', 20),
            ('homework', 'Homework 1', 10),
            ('homework', 'Homework 2', 10),
            ('midterm', 'Midterm Exam', 30),
            ('project', 'Class Project', 25),
        ]
        
        grades_count = 0
        for subject in all_subjects:
            subject_id, subject_name, class_id, teacher_id = subject
            
            if class_id in students_by_class:
                for grade_type, title, max_score in grade_types:
                    grade_date = today - timedelta(days=random.randint(5, 60))
                    
                    for student in students_by_class[class_id]:
                        student_id = student[0]
                        # Generate realistic scores (60-100% range mostly)
                        score = round(random.uniform(max_score * 0.5, max_score), 1)
                        
                        cur.execute("""
                            INSERT INTO grades (student_id, subject_id, grade_type, title, score, max_score, date)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (student_id, subject_id, grade_type, title, score, max_score, grade_date))
                        grades_count += 1
        
        print(f"  Created {grades_count} grade records")
        
        # =============================================
        # 8. CREATE HOMEWORK
        # =============================================
        print("Creating homework assignments...")
        
        homework_titles = [
            ('Chapter Review Questions', 'Complete the review questions at the end of chapter 3'),
            ('Case Study Analysis', 'Analyze the given case study and write a 2-page report'),
            ('Research Assignment', 'Research and present findings on the assigned topic'),
            ('Practical Exercise', 'Complete the hands-on exercises in the lab manual'),
            ('Group Project Proposal', 'Submit your group project proposal with timeline'),
        ]
        
        homework_count = 0
        for subject in all_subjects:
            subject_id, subject_name, class_id, teacher_id = subject
            
            # Create 2-3 homework per subject
            for i in range(random.randint(2, 3)):
                title, description = random.choice(homework_titles)
                title = f"{title} - {subject_name[:20]}"
                due_date = today + timedelta(days=random.randint(-10, 20))
                
                cur.execute("""
                    INSERT INTO homework (class_id, subject_id, teacher_id, title, description, due_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (class_id, subject_id, teacher_id, title, description, due_date))
                homework_count += 1
        
        print(f"  Created {homework_count} homework assignments")
        
        # =============================================
        # 9. CREATE WEEKLY TOPICS
        # =============================================
        print("Creating weekly topics...")
        
        topics_count = 0
        for subject in all_subjects:
            subject_id, subject_name, class_id, teacher_id = subject
            
            # Create 8 weeks of topics
            for week in range(1, 9):
                topic_date = today - timedelta(days=(8-week) * 7)
                topic_titles = [
                    f"Week {week}: Introduction and Overview",
                    f"Week {week}: Core Concepts",
                    f"Week {week}: Practical Applications",
                    f"Week {week}: Case Studies",
                    f"Week {week}: Advanced Topics",
                    f"Week {week}: Review and Practice",
                    f"Week {week}: Project Work",
                    f"Week {week}: Assessment Preparation",
                ]
                
                cur.execute("""
                    INSERT INTO weekly_topics (class_id, subject_id, teacher_id, week_number, topic, description, date_covered)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (class_id, subject_id, teacher_id, week, topic_titles[week-1], f"Topics covered in week {week} of {subject_name}", topic_date))
                topics_count += 1
        
        print(f"  Created {topics_count} weekly topics")
        
        # Commit all changes
        conn.commit()
        
        print("\n" + "="*50)
        print("✅ SAMPLE DATA INSERTED SUCCESSFULLY!")
        print("="*50)
        print("\n📋 SUMMARY:")
        print(f"   • Teachers: 5 (password: teacher123)")
        print(f"   • Students: 40 (10 per semester, password: student123)")
        print(f"   • Subjects: 20 (5 per semester)")
        print(f"   • Attendance Records: {attendance_count}")
        print(f"   • Grade Records: {grades_count}")
        print(f"   • Homework Assignments: {homework_count}")
        print(f"   • Weekly Topics: {topics_count}")
        print("\n🔑 LOGIN CREDENTIALS:")
        print("   Admin: admin / admin123")
        print("   Teachers: teacher1-5 / teacher123")
        print("   Students: student1_1, student1_2, etc. / student123")
        print("="*50)
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    insert_sample_data()
