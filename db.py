"""
Database connection and helper functions for MIS System
"""
import pg8000
import pg8000.native
from config import config


def get_db_connection():
    """
    Create and return a database connection.
    Returns rows as dictionaries using pg8000.
    """
    try:
        conn = pg8000.connect(
            host=config.DB_HOST,
            port=int(config.DB_PORT),
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None


def row_to_dict(cursor, row):
    """Convert a row to a dictionary using cursor description"""
    if row is None:
        return None
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))


def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """
    Execute a database query safely.
    
    Args:
        query: SQL query string
        params: Query parameters (tuple or dict)
        fetch_one: Return single row
        fetch_all: Return all rows
    
    Returns:
        Query result or None
    """
    conn = get_db_connection()
    if not conn:
        return [] if fetch_all else None
    
    try:
        cursor = conn.cursor()
        # pg8000 requires params to be a tuple or None
        if params is None:
            cursor.execute(query)
        else:
            cursor.execute(query, params)
        
        result = None
        if fetch_one:
            row = cursor.fetchone()
            result = row_to_dict(cursor, row)
            conn.commit()
        elif fetch_all:
            rows = cursor.fetchall()
            result = [row_to_dict(cursor, row) for row in rows] if rows else []
            conn.commit()  # Critical: commit DELETE queries with RETURNING
        else:
            conn.commit()
            result = cursor.rowcount
        
        cursor.close()
        conn.close()
        return result
    
    except Exception as e:
        print(f"Query error: {e}")
        conn.rollback()
        conn.close()
        return [] if fetch_all else None


def execute_insert_returning(query, params=None):
    """
    Execute an INSERT query and return the inserted row's ID.
    
    Args:
        query: SQL INSERT query with RETURNING clause
        params: Query parameters
    
    Returns:
        Inserted row ID or None
    """
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        result = row_to_dict(cursor, row)
        conn.commit()
        cursor.close()
        conn.close()
        return result['id'] if result else None
    
    except Exception as e:
        print(f"Insert error: {e}")
        conn.rollback()
        conn.close()
        return None


# =============================================
# SYSTEM SETTINGS
# =============================================

def get_current_cycle():
    """Get the current academic cycle (1 or 2)"""
    query = "SELECT value FROM system_settings WHERE key = 'current_cycle'"
    result = execute_query(query, fetch_one=True)
    return int(result['value']) if result else 1


def set_current_cycle(cycle):
    """Set the current academic cycle (1 or 2)"""
    query = """
        INSERT INTO system_settings (key, value, description, updated_at) 
        VALUES ('current_cycle', %s, 'Academic cycle: 1 = Sem 1+3 active, 2 = Sem 2+4 active', CURRENT_TIMESTAMP)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
    """
    return execute_query(query, (str(cycle),))


def get_semester_for_year(year, cycle=None):
    """Get the active semester for a year based on the current cycle"""
    if cycle is None:
        cycle = get_current_cycle()
    
    if year == 1:
        return 1 if cycle == 1 else 2
    else:  # year == 2
        return 3 if cycle == 1 else 4


# =============================================
# STUDENT QUERIES (UPDATED FOR YEAR/SHIFT/SECTION)
# =============================================

def get_students_by_year_shift_section(year, shift, section):
    """Get students by year, shift, and section (the new primary way to query students)"""
    query = """
        SELECT s.*, u.full_name, u.username, u.email
        FROM students s
        JOIN users u ON s.user_id = u.id
        WHERE s.year = %s AND s.shift = %s AND s.section = %s
        ORDER BY u.full_name
    """
    return execute_query(query, (year, shift, section), fetch_all=True)


def get_students_by_semester(semester, shift, section):
    """Get students by semester, shift, and section"""
    year = 1 if semester <= 2 else 2
    query = """
        SELECT s.*, u.full_name, u.username, u.email
        FROM students s
        JOIN users u ON s.user_id = u.id
        WHERE s.semester = %s AND s.shift = %s AND s.section = %s
        ORDER BY u.full_name
    """
    return execute_query(query, (semester, shift, section), fetch_all=True)


def get_student_count_by_year_shift_section(year, shift, section):
    """Get count of students in a year/shift/section"""
    query = """
        SELECT COUNT(*) as count FROM students
        WHERE year = %s AND shift = %s AND section = %s
    """
    result = execute_query(query, (year, shift, section), fetch_one=True)
    return result['count'] if result else 0


def create_student_with_semester(user_id, year, semester, shift, section, student_number=None, phone=None):
    """Create student with semester assignment and auto-link to class"""
    # Look up matching class_id
    class_id = None
    if semester and shift and section:
        cls = execute_query(
            "SELECT id FROM classes WHERE semester = %s AND shift = %s AND section = %s AND is_active = true LIMIT 1",
            (semester, shift, section), fetch_one=True
        )
        if cls:
            class_id = cls['id']

    query = """
        INSERT INTO students (user_id, year, semester, shift, section, student_number, phone, class_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (user_id, year, semester, shift, section, student_number, phone, class_id))


def get_student_counts_by_semester():
    """Get student counts grouped by semester, shift"""
    query = """
        SELECT semester, shift, section, COUNT(*) as count
        FROM students
        WHERE semester IS NOT NULL
        GROUP BY semester, shift, section
        ORDER BY semester, shift, section
    """
    results = execute_query(query, fetch_all=True) or []
    
    # Organize into a structured format
    stats = {1: {'morning': 0, 'night': 0, 'total': 0},
             2: {'morning': 0, 'night': 0, 'total': 0},
             3: {'morning': 0, 'night': 0, 'total': 0},
             4: {'morning': 0, 'night': 0, 'total': 0}}
    
    for r in results:
        sem = r['semester']
        shift = r['shift']
        count = r['count']
        if sem in stats and shift in stats[sem]:
            stats[sem][shift] += count
            stats[sem]['total'] += count
    
    return stats


# =============================================
# USER QUERIES
# =============================================

def get_user_by_username(username):
    """Get user by username"""
    query = "SELECT * FROM users WHERE username = %s"
    return execute_query(query, (username,), fetch_one=True)


def get_user_by_email(email):
    """Get user by email"""
    query = "SELECT * FROM users WHERE email = %s"
    return execute_query(query, (email,), fetch_one=True)


def get_user_by_id(user_id):
    """Get user by ID"""
    query = "SELECT * FROM users WHERE id = %s"
    return execute_query(query, (user_id,), fetch_one=True)


def create_user(username, password_hash, full_name, role, email=None, plain_password=None):
    """Create a new user"""
    query = """
        INSERT INTO users (username, password_hash, full_name, role, email, plain_password)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (username, password_hash, full_name, role, email, plain_password))


def get_all_users():
    """Get all users with password hash and plain password"""
    query = "SELECT id, username, full_name, role, email, created_at, password_hash, plain_password FROM users ORDER BY id"
    return execute_query(query, fetch_all=True)


def delete_user(user_id):
    """Delete a user"""
    query = "DELETE FROM users WHERE id = %s"
    return execute_query(query, (user_id,))


def update_user(user_id, full_name, email=None):
    """Update user basic info"""
    query = "UPDATE users SET full_name = %s, email = %s WHERE id = %s"
    return execute_query(query, (full_name, email, user_id))


def update_user_complete(user_id, username, full_name, email, role):
    """Update user with username and role"""
    query = "UPDATE users SET username = %s, full_name = %s, email = %s, role = %s WHERE id = %s"
    return execute_query(query, (username, full_name, email, role, user_id))


def update_user_password(user_id, password_hash, plain_password=None):
    """Update user password"""
    query = "UPDATE users SET password_hash = %s, plain_password = %s WHERE id = %s"
    return execute_query(query, (password_hash, plain_password, user_id))


# =============================================
# CLASS QUERIES
# =============================================

def get_all_classes():
    """Get all classes ordered by year, semester, section, shift"""
    query = """
        SELECT * FROM classes 
        ORDER BY year, semester, section, shift
    """
    return execute_query(query, fetch_all=True)


def get_class_student_counts():
    """Get student counts for each class (semester, shift, section) and semester totals"""
    # Count students by their semester/shift/section columns (not class_id)
    # This matches how get_students_by_semester retrieves students
    query = """
        SELECT 
            s.semester,
            s.shift,
            s.section,
            COUNT(s.id) as student_count
        FROM students s
        WHERE s.semester IS NOT NULL 
          AND s.shift IS NOT NULL 
          AND s.section IS NOT NULL
        GROUP BY s.semester, s.shift, s.section
        ORDER BY s.semester, s.shift, s.section
    """
    results = execute_query(query, fetch_all=True)
    
    # Create dictionaries for easy lookup
    counts = {}
    semester_totals = {1: 0, 2: 0, 3: 0, 4: 0}
    
    for row in results:
        key = f"{row['semester']}_{row['shift']}_{row['section']}"
        counts[key] = row['student_count']
        semester_totals[row['semester']] += row['student_count']
    
    return counts, semester_totals


def get_class_by_id(class_id):
    """Get class by ID"""
    query = "SELECT * FROM classes WHERE id = %s"
    return execute_query(query, (class_id,), fetch_one=True)


def get_active_classes():
    """Get only active classes"""
    query = """
        SELECT * FROM classes 
        WHERE is_active = true
        ORDER BY year, semester, section, shift
    """
    return execute_query(query, fetch_all=True)


def get_classes_by_year_semester(year, semester):
    """Get classes for a specific year and semester"""
    query = """
        SELECT * FROM classes 
        WHERE year = %s AND semester = %s
        ORDER BY section, shift
    """
    return execute_query(query, (year, semester), fetch_all=True)


def create_class(name, year, semester, section, shift, description=None):
    """Create a new class with all required fields"""
    query = """
        INSERT INTO classes (name, year, semester, section, shift, description)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (name, year, semester, section, shift, description))


def update_class(class_id, name, year, semester, section, shift, description=None, is_active=True):
    """Update a class"""
    query = """
        UPDATE classes 
        SET name = %s, year = %s, semester = %s, section = %s, shift = %s, description = %s, is_active = %s
        WHERE id = %s
    """
    return execute_query(query, (name, year, semester, section, shift, description, is_active, class_id))


def toggle_class_active(class_id, is_active):
    """Toggle class active status"""
    query = "UPDATE classes SET is_active = %s WHERE id = %s"
    return execute_query(query, (is_active, class_id))


def delete_class(class_id):
    """Delete a class"""
    query = "DELETE FROM classes WHERE id = %s"
    return execute_query(query, (class_id,))


# =============================================
# TEACHER QUERIES
# =============================================

def create_teacher(user_id, department=None, phone=None):
    """Create teacher profile"""
    query = """
        INSERT INTO teachers (user_id, department, phone)
        VALUES (%s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (user_id, department, phone))


def get_teacher_by_user_id(user_id):
    """Get teacher by user ID"""
    query = """
        SELECT t.*, u.full_name, u.username, u.email
        FROM teachers t
        JOIN users u ON t.user_id = u.id
        WHERE t.user_id = %s
    """
    return execute_query(query, (user_id,), fetch_one=True)


def get_all_teachers():
    """Get all teachers with user info"""
    query = """
        SELECT t.*, u.full_name, u.username, u.email
        FROM teachers t
        JOIN users u ON t.user_id = u.id
        ORDER BY u.full_name
    """
    return execute_query(query, fetch_all=True)


def get_all_teachers_with_subjects():
    """Get all teachers with their assigned subjects"""
    query = """
        SELECT t.id as teacher_id, t.user_id, t.department, t.phone, u.full_name, u.username, u.email,
               COALESCE(
                   (SELECT COUNT(*) FROM subjects WHERE teacher_id = t.id), 0
               ) as subject_count
        FROM teachers t
        JOIN users u ON t.user_id = u.id
        ORDER BY u.full_name
    """
    return execute_query(query, fetch_all=True)


def get_subjects_by_teacher_id(teacher_id):
    """Get all subjects assigned to a teacher with class info via teacher_assignments"""
    query = """
        SELECT s.id, s.name, c.name as class_name, c.year, c.semester, c.section, c.shift,
               ta.id as assignment_id
        FROM teacher_assignments ta
        JOIN subjects s ON ta.subject_id = s.id
        JOIN classes c ON ta.class_id = c.id
        WHERE ta.teacher_id = %s
        ORDER BY s.name, c.year, c.section
    """
    return execute_query(query, (teacher_id,), fetch_all=True)


# =============================================
# STUDENT QUERIES
# =============================================

def create_student(user_id, class_id=None, student_number=None, phone=None):
    """Create student profile"""
    query = """
        INSERT INTO students (user_id, class_id, student_number, phone)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (user_id, class_id, student_number, phone))


def get_student_by_user_id(user_id):
    """Get student by user ID"""
    query = """
        SELECT s.*, u.full_name, u.username, u.email, c.name as class_name
        FROM students s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN classes c ON s.class_id = c.id
        WHERE s.user_id = %s
    """
    return execute_query(query, (user_id,), fetch_one=True)


def get_students_by_class(class_id):
    """Get all students in a class"""
    query = """
        SELECT s.*, u.full_name, u.username, u.email
        FROM students s
        JOIN users u ON s.user_id = u.id
        WHERE s.class_id = %s
        ORDER BY u.full_name
    """
    return execute_query(query, (class_id,), fetch_all=True)


def get_all_students():
    """Get all students"""
    query = """
        SELECT s.*, u.full_name, u.username, u.email, c.name as class_name, c.year
        FROM students s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN classes c ON s.class_id = c.id
        ORDER BY u.full_name
    """
    return execute_query(query, fetch_all=True)


def get_student_by_id(student_id):
    """Get student by ID with year/shift/section"""
    query = """
        SELECT s.*, u.full_name, u.username, u.email
        FROM students s
        JOIN users u ON s.user_id = u.id
        WHERE s.id = %s
    """
    return execute_query(query, (student_id,), fetch_one=True)


def update_student(student_id, full_name, email, class_id, student_number, phone):
    """Update student information"""
    query = """
        UPDATE students SET class_id = %s, student_number = %s, phone = %s
        WHERE id = %s
    """
    result = execute_query(query, (class_id, student_number, phone, student_id))
    
    # Also update user info
    student = get_student_by_id(student_id)
    if student:
        query2 = "UPDATE users SET full_name = %s, email = %s WHERE id = %s"
        execute_query(query2, (full_name, email, student['user_id']))
    
    return result


def delete_student(student_id):
    """Delete a student and their user account"""
    student = get_student_by_id(student_id)
    if student:
        # Delete student profile
        execute_query("DELETE FROM students WHERE id = %s", (student_id,))
        # Delete user account
        execute_query("DELETE FROM users WHERE id = %s", (student['user_id'],))
        return True
    return False


def get_students_filtered(year=None, class_id=None):
    """Get students filtered by year and/or class"""
    query = """
        SELECT s.*, u.full_name, u.username, u.email, c.name as class_name, c.year
        FROM students s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN classes c ON s.class_id = c.id
        WHERE 1=1
    """
    params = []
    
    if year:
        query += " AND c.year = %s"
        params.append(year)
    
    if class_id:
        query += " AND s.class_id = %s"
        params.append(class_id)
    
    query += " ORDER BY u.full_name"
    
    return execute_query(query, tuple(params) if params else None, fetch_all=True)


# =============================================
# STUDENT ENROLLMENT QUERIES
# =============================================

def get_available_subjects_for_student(student_id):
    """Get subjects available for student's semester (enrolled + not enrolled)"""
    query = """
        SELECT s.*, 
               CASE WHEN se.id IS NOT NULL THEN true ELSE false END as is_enrolled
        FROM students st
        JOIN classes c ON st.class_id = c.id
        JOIN subjects s ON s.semester = c.semester
        LEFT JOIN student_enrollments se ON se.student_id = st.id AND se.subject_id = s.id
        WHERE st.id = %s
        ORDER BY s.name
    """
    return execute_query(query, (student_id,), fetch_all=True)


def get_enrolled_subjects_for_student(student_id):
    """Get subjects student is enrolled in"""
    query = """
        SELECT s.*, se.enrolled_at
        FROM student_enrollments se
        JOIN subjects s ON se.subject_id = s.id
        WHERE se.student_id = %s
        ORDER BY s.name
    """
    return execute_query(query, (student_id,), fetch_all=True)


def enroll_student_in_subject(student_id, subject_id):
    """Enroll a student in a subject"""
    # First check if already enrolled
    check_query = "SELECT id FROM student_enrollments WHERE student_id = %s AND subject_id = %s"
    existing = execute_query(check_query, (student_id, subject_id), fetch_one=True)
    if existing:
        return False  # Already enrolled
    
    # Insert new enrollment
    query = """
        INSERT INTO student_enrollments (student_id, subject_id)
        VALUES (%s, %s)
        RETURNING id
    """
    result = execute_query(query, (student_id, subject_id), fetch_one=True)
    return result is not None


def unenroll_student_from_subject(student_id, subject_id):
    """Unenroll a student from a subject"""
    query = "DELETE FROM student_enrollments WHERE student_id = %s AND subject_id = %s"
    execute_query(query, (student_id, subject_id))
    return True


def get_enrolled_students_for_subject(subject_id, class_id=None):
    """Get all students enrolled in a specific subject, optionally filtered by class"""
    query = """
        SELECT s.*, u.full_name, u.username, u.email, c.name as class_name,
               se.enrolled_at
        FROM student_enrollments se
        JOIN students s ON se.student_id = s.id
        JOIN users u ON s.user_id = u.id
        LEFT JOIN classes c ON s.class_id = c.id
        WHERE se.subject_id = %s
    """
    params = [subject_id]
    
    # Filter by class if provided (to show only students from specific section)
    if class_id:
        query += " AND s.class_id = %s"
        params.append(class_id)
    
    query += " ORDER BY u.full_name"
    return execute_query(query, tuple(params), fetch_all=True)


# =============================================
# ENROLLMENT PERIODS QUERIES
# =============================================

def create_enrollment_period(semester, start_date, end_date, description, created_by):
    """Create a new enrollment period for a semester"""
    query = """
        INSERT INTO enrollment_periods (semester, start_date, end_date, description, created_by)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (semester, start_date, end_date, description, created_by))


def get_active_enrollment_period(semester):
    """Get active enrollment period for a semester (if any)"""
    query = """
        SELECT * FROM enrollment_periods
        WHERE semester = %s
        AND CURRENT_TIMESTAMP BETWEEN start_date AND end_date
        ORDER BY created_at DESC
        LIMIT 1
    """
    return execute_query(query, (semester,), fetch_one=True)


def get_all_enrollment_periods(semester=None):
    """Get all enrollment periods, optionally filtered by semester"""
    query = """
        SELECT ep.*, u.full_name as created_by_name
        FROM enrollment_periods ep
        LEFT JOIN users u ON ep.created_by = u.id
    """
    if semester:
        query += " WHERE ep.semester = %s"
        query += " ORDER BY ep.created_at DESC"
        return execute_query(query, (semester,), fetch_all=True)
    else:
        query += " ORDER BY ep.semester, ep.created_at DESC"
        return execute_query(query, fetch_all=True)


def is_enrollment_active(semester):
    """Check if enrollment is currently active for a semester"""
    period = get_active_enrollment_period(semester)
    return period is not None


def delete_enrollment_period(period_id):
    """Delete an enrollment period"""
    query = "DELETE FROM enrollment_periods WHERE id = %s"
    return execute_query(query, (period_id,))


# =============================================
# SUBJECT QUERIES
# =============================================

def get_subject_count_by_class(class_id):
    """Get the number of subjects for a class (max should be 5)"""
    query = "SELECT COUNT(*) as count FROM subjects WHERE class_id = %s"
    result = execute_query(query, (class_id,), fetch_one=True)
    return result['count'] if result else 0


def create_subject(name, semester, description=None, credits=6):
    """Create a new subject for a specific semester or return existing subject ID"""
    # Check if subject with this name already exists in this semester
    existing = execute_query(
        "SELECT id FROM subjects WHERE LOWER(name) = LOWER(%s) AND semester = %s",
        (name, semester),
        fetch_one=True
    )
    if existing:
        return existing['id']
    
    query = """
        INSERT INTO subjects (name, semester, description, credits)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (name, semester, description, credits))


def get_subject_by_name_and_class(name, class_id):
    """Get subject by name with assignment info for a specific class"""
    query = """
        SELECT s.*, ta.id as assignment_id, ta.teacher_id
        FROM subjects s
        LEFT JOIN teacher_assignments ta ON s.id = ta.subject_id AND ta.class_id = %s
        WHERE s.name = %s
    """
    return execute_query(query, (class_id, name), fetch_one=True)


def get_subjects_by_class(class_id):
    """Get all subjects assigned to a class with their teachers"""
    query = """
        SELECT DISTINCT s.*, 
               ta.id as assignment_id,
               t.id as teacher_id, u.full_name as teacher_name
        FROM subjects s
        JOIN teacher_assignments ta ON s.id = ta.subject_id
        LEFT JOIN teachers t ON  ta.teacher_id = t.id
        LEFT JOIN users u ON t.user_id = u.id
        WHERE ta.class_id = %s
        ORDER BY s.name
    """
    return execute_query(query, (class_id,), fetch_all=True)


def get_subjects_by_teacher(teacher_id):
    """Get all subjects taught by a teacher with class info"""
    query = """
        SELECT DISTINCT s.*, 
               c.name as class_name, c.year, c.semester, c.section, c.shift,
               ta.id as assignment_id, ta.class_id
        FROM subjects s
        JOIN teacher_assignments ta ON s.id = ta.subject_id
        JOIN classes c ON ta.class_id = c.id
        WHERE ta.teacher_id = %s
        ORDER BY c.year, c.semester, c.section, s.name
    """
    return execute_query(query, (teacher_id,), fetch_all=True)


def get_all_subjects():
    """Get all subjects with their teacher assignments"""
    query = """
        SELECT DISTINCT s.*, 
               c.name as class_name, c.year, c.semester, c.section, c.shift,
               ta.id as assignment_id,
               t.id as teacher_id,
               u.full_name as teacher_name
        FROM subjects s
        LEFT JOIN teacher_assignments ta ON s.id = ta.subject_id
        LEFT JOIN classes c ON ta.class_id = c.id
        LEFT JOIN teachers t ON ta.teacher_id = t.id
        LEFT JOIN users u ON t.user_id = u.id
        ORDER BY s.name, c.year, c.semester, c.section
    """
    return execute_query(query, fetch_all=True)


def get_unique_subjects_by_semester():
    """Get unique subjects grouped by year/semester (for dropdown selection)"""
    query = """
        SELECT DISTINCT s.name,
               CASE WHEN s.semester IN (1,2) THEN 1 ELSE 2 END AS year,
               s.semester
        FROM subjects s
        WHERE s.semester IS NOT NULL
        ORDER BY s.semester, s.name
    """
    return execute_query(query, fetch_all=True)


def get_subjects_grouped_by_semester():
    """Get all subjects grouped by semester with their assignment info"""
    query = """
        SELECT s.id, s.name, s.semester, s.description, s.credits, s.results_published,
               c.year, c.section,
               ta.id as assignment_id,
               t.id as teacher_id, u.full_name as teacher_name
        FROM subjects s
        LEFT JOIN teacher_assignments ta ON s.id = ta.subject_id
        LEFT JOIN classes c ON ta.class_id = c.id
        LEFT JOIN teachers t ON ta.teacher_id = t.id
        LEFT JOIN users u ON t.user_id = u.id
        WHERE s.semester IS NOT NULL
        ORDER BY c.year, s.semester, c.section, s.name
    """
    return execute_query(query, fetch_all=True)


def get_semesters():
    """Get list of unique semesters (year/semester combinations)"""
    return [
        {'year': 1, 'semester': 1, 'name': 'Year 1 - Semester 1'},
        {'year': 1, 'semester': 2, 'name': 'Year 1 - Semester 2'},
        {'year': 2, 'semester': 3, 'name': 'Year 2 - Semester 3'},
        {'year': 2, 'semester': 4, 'name': 'Year 2 - Semester 4'},
    ]


def get_first_class_for_semester(year, semester):
    """Get the first class ID for a given year/semester (for subject creation)"""
    query = """
        SELECT id FROM classes 
        WHERE year = %s AND semester = %s 
        ORDER BY id LIMIT 1
    """
    result = execute_query(query, (year, semester), fetch_one=True)
    return result['id'] if result else None


def get_subject_by_id(subject_id):
    """Get subject by ID with teacher assignments"""
    query = """
        SELECT s.*,
               ta.id as assignment_id,
               ta.class_id,
               c.year, c.semester, c.section, c.shift,
               t.id as teacher_id,
               u.full_name as teacher_name
        FROM subjects s
        LEFT JOIN teacher_assignments ta ON s.id = ta.subject_id
        LEFT JOIN classes c ON ta.class_id = c.id
        LEFT JOIN teachers t ON ta.teacher_id = t.id
        LEFT JOIN users u ON t.user_id = u.id
        WHERE s.id = %s
    """
    return execute_query(query, (subject_id,), fetch_one=True)


def update_subject(subject_id, name, semester, description=None, credits=6):
    """Update a subject's name, semester, description and credits"""
    query = """
        UPDATE subjects SET name = %s, semester = %s, description = %s, credits = %s
        WHERE id = %s
    """
    return execute_query(query, (name, semester, description, credits, subject_id))


def update_subject_teacher(assignment_id, teacher_id):
    """Update the teacher for a specific assignment"""
    query = "UPDATE teacher_assignments SET teacher_id = %s WHERE id = %s"
    return execute_query(query, (teacher_id, assignment_id))


def delete_subject(subject_id):
    """Delete a subject"""
    query = "DELETE FROM subjects WHERE id = %s"
    return execute_query(query, (subject_id,))


# =============================================
# ATTENDANCE QUERIES
# =============================================

def record_attendance(student_id, subject_id, teacher_id, date, status, notes=None):
    """Record attendance for a student"""
    query = """
        INSERT INTO attendance (student_id, subject_id, teacher_id, date, status, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (student_id, subject_id, date) 
        DO UPDATE SET status = EXCLUDED.status, notes = EXCLUDED.notes
        RETURNING id
    """
    return execute_insert_returning(query, (student_id, subject_id, teacher_id, date, status, notes))


def get_attendance_by_student(student_id):
    """Get all attendance records for a student"""
    query = """
        SELECT a.*, s.name as subject_name
        FROM attendance a
        JOIN subjects s ON a.subject_id = s.id
        WHERE a.student_id = %s
        ORDER BY a.date DESC
    """
    return execute_query(query, (student_id,), fetch_all=True)


def get_attendance_by_subject_date(subject_id, date):
    """Get attendance for a subject on a specific date"""
    query = """
        SELECT a.*, u.full_name as student_name, st.student_number
        FROM attendance a
        JOIN students st ON a.student_id = st.id
        JOIN users u ON st.user_id = u.id
        WHERE a.subject_id = %s AND a.date = %s
        ORDER BY u.full_name
    """
    return execute_query(query, (subject_id, date), fetch_all=True)


def get_attendance_logs(subject_id, student_id=None, date_from=None, date_to=None, status=None):
    """Get attendance logs with filtering"""
    query = """
        SELECT a.*, u.full_name as student_name, st.student_number, s.name as subject_name
        FROM attendance a
        JOIN students st ON a.student_id = st.id
        JOIN users u ON st.user_id = u.id
        JOIN subjects s ON a.subject_id = s.id
        WHERE a.subject_id = %s
    """
    params = [subject_id]
    
    if student_id:
        query += " AND a.student_id = %s"
        params.append(student_id)
    if date_from:
        query += " AND a.date >= %s"
        params.append(date_from)
    if date_to:
        query += " AND a.date <= %s"
        params.append(date_to)
    if status:
        query += " AND a.status = %s"
        params.append(status)
    
    query += " ORDER BY a.date DESC, u.full_name"
    return execute_query(query, tuple(params), fetch_all=True)


def get_attendance_summary(subject_id):
    """Get attendance summary by student for a subject"""
    query = """
        SELECT st.id as student_id, u.full_name as student_name, st.student_number,
               COUNT(*) as total_classes,
               SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) as present_count,
               SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) as absent_count,
               SUM(CASE WHEN a.status = 'late' THEN 1 ELSE 0 END) as late_count,
               SUM(CASE WHEN a.status = 'excused' THEN 1 ELSE 0 END) as excused_count
        FROM attendance a
        JOIN students st ON a.student_id = st.id
        JOIN users u ON st.user_id = u.id
        WHERE a.subject_id = %s
        GROUP BY st.id, u.full_name, st.student_number
        ORDER BY u.full_name
    """
    return execute_query(query, (subject_id,), fetch_all=True)


def get_attendance_dates(subject_id):
    """Get all unique dates for attendance in a subject"""
    query = """
        SELECT DISTINCT date FROM attendance 
        WHERE subject_id = %s ORDER BY date DESC
    """
    return execute_query(query, (subject_id,), fetch_all=True)


# =============================================
# GRADES QUERIES
# =============================================

def add_grade(student_id, subject_id, teacher_id, grade_type, title, score, max_score, date, notes=None, component_id=None, published=False):
    """Add a grade for a student (default unpublished/draft)"""
    query = """
        INSERT INTO grades (student_id, subject_id, teacher_id, grade_type, title, score, max_score, date, notes, component_id, published)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (student_id, subject_id, teacher_id, grade_type, title, score, max_score, date, notes, component_id, published))


def upsert_grade(student_id, subject_id, teacher_id, grade_type, title, score, max_score, date, component_id, notes=None, published=False):
    """Update existing grade or insert new one for a student/component combination (default unpublished/draft)"""
    print(f"\n>>> UPSERT_GRADE CALLED <<<")
    print(f"  student_id: {student_id}")
    print(f"  subject_id: {subject_id}")
    print(f"  teacher_id: {teacher_id}")
    print(f"  component_id: {component_id}")
    print(f"  score: {score}")
    print(f"  max_score: {max_score}")
    print(f"  date: {date}")
    print(f"  grade_type: {grade_type}")
    print(f"  title: {title}")
    print(f"  published: {published}")
    
    # First, check if a grade exists for this student and component
    check_query = """
        SELECT id FROM grades 
        WHERE student_id = %s AND component_id = %s
        ORDER BY date DESC, id DESC
        LIMIT 1
    """
    print(f"  Checking for existing grade...")
    existing = execute_query(check_query, (student_id, component_id), fetch_one=True)
    
    if existing:
        print(f"  Found existing grade ID: {existing['id']} - UPDATING")
        # Update existing grade
        update_query = """
            UPDATE grades 
            SET score = %s, max_score = %s, date = %s, notes = %s, grade_type = %s, title = %s, published = %s
            WHERE id = %s
            RETURNING id
        """
        result = execute_insert_returning(update_query, (score, max_score, date, notes, grade_type, title, published, existing['id']))
        print(f"  Update result: {result}")
        return result
    else:
        print(f"  No existing grade - INSERTING")
        # Insert new grade
        insert_query = """
            INSERT INTO grades (student_id, subject_id, teacher_id, grade_type, title, score, max_score, date, notes, component_id, published)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        result = execute_insert_returning(insert_query, (student_id, subject_id, teacher_id, grade_type, title, score, max_score, date, notes, component_id, published))
        print(f"  Insert result: {result}")
        return result


def get_grades_by_student(student_id):
    """Get all grades for a student"""
    query = """
        SELECT g.*, s.name as subject_name
        FROM grades g
        JOIN subjects s ON g.subject_id = s.id
        WHERE g.student_id = %s
        ORDER BY g.date DESC
    """
    return execute_query(query, (student_id,), fetch_all=True)


def get_grades_by_subject(subject_id):
    """Get all grades for a subject"""
    query = """
        SELECT g.*, u.full_name as student_name, st.student_number
        FROM grades g
        JOIN students st ON g.student_id = st.id
        JOIN users u ON st.user_id = u.id
        WHERE g.subject_id = %s
        ORDER BY g.date DESC, u.full_name
    """
    return execute_query(query, (subject_id,), fetch_all=True)


def get_student_grades_for_subject(student_id, subject_id):
    """Get student's grades for a specific subject with component details (only published grades for students)"""
    query = """
        SELECT 
            gc.id as component_id,
            gc.component_type,
            gc.component_name,
            gc.max_score,
            gc.weight_percentage,
            gc.display_order,
            g.score,
            g.date as grade_date,
            g.published
        FROM grade_components gc
        LEFT JOIN grades g ON gc.id = g.component_id 
            AND g.student_id = %s 
            AND g.subject_id = %s
            AND g.published = TRUE
        WHERE gc.subject_id = %s
        ORDER BY gc.display_order, gc.component_type, gc.id
    """
    return execute_query(query, (student_id, subject_id, subject_id), fetch_all=True)


def publish_grades_for_subject(subject_id, class_id):
    """Publish all draft grades for a specific subject and class"""
    query = """
        UPDATE grades 
        SET published = TRUE
        WHERE subject_id = %s 
        AND student_id IN (
            SELECT id FROM students WHERE class_id = %s
        )
        AND published = FALSE
    """
    return execute_query(query, (subject_id, class_id))


def get_unpublished_grade_count(subject_id, class_id):
    """Get count of unpublished grades for a subject/class"""
    query = """
        SELECT COUNT(*) as count
        FROM grades g
        JOIN students s ON g.student_id = s.id
        WHERE g.subject_id = %s 
        AND s.class_id = %s
        AND g.published = FALSE
    """
    result = execute_query(query, (subject_id, class_id), fetch_one=True)
    return result['count'] if result else 0


def toggle_subject_results_published(subject_id, published):
    """Admin: Toggle results visibility for a subject (final transcript)"""
    query = """
        UPDATE subjects 
        SET results_published = %s
        WHERE id = %s
    """
    return execute_query(query, (published, subject_id))


def publish_semester_results(semester):
    """Admin: Publish all subject results for an entire semester"""
    query = """
        UPDATE subjects 
        SET results_published = TRUE
        WHERE semester = %s
    """
    return execute_query(query, (semester,))


# =============================================
# HOMEWORK QUERIES
# =============================================

def create_homework(class_id, subject_id, teacher_id, title, description, due_date, filename=None, file_path=None, file_type=None, file_size=None):
    """Create a new homework assignment"""
    query = """
        INSERT INTO homework (class_id, subject_id, teacher_id, title, description, due_date, filename, file_path, file_type, file_size)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (class_id, subject_id, teacher_id, title, description, due_date, filename, file_path, file_type, file_size))


def get_homework_by_class(class_id):
    """Get all homework for a class"""
    query = """
        SELECT h.*, s.name as subject_name, u.full_name as teacher_name
        FROM homework h
        JOIN subjects s ON h.subject_id = s.id
        LEFT JOIN teachers t ON h.teacher_id = t.id
        LEFT JOIN users u ON t.user_id = u.id
        WHERE h.class_id = %s
        ORDER BY h.due_date DESC
    """
    return execute_query(query, (class_id,), fetch_all=True)


def get_homework_by_teacher(teacher_id):
    """Get all homework created by a teacher (with file information)"""
    query = """
        SELECT h.*, s.name as subject_name, c.name as class_name
        FROM homework h
        JOIN subjects s ON h.subject_id = s.id
        JOIN classes c ON h.class_id = c.id
        WHERE h.teacher_id = %s
        ORDER BY h.due_date DESC
    """
    return execute_query(query, (teacher_id,), fetch_all=True)


def delete_homework(homework_id, teacher_id):
    """Delete homework (mark as done) - only the teacher who created it can delete"""
    query = """
        DELETE FROM homework
        WHERE id = %s AND teacher_id = %s
        RETURNING id
    """
    return execute_insert_returning(query, (homework_id, teacher_id))


# =============================================
# GRADE COMPONENTS QUERIES
# =============================================

def add_grade_component(subject_id, component_type, component_name, max_score, weight_percentage, display_order=0):
    """Add a grade component to a subject's grading rubric"""
    query = """
        INSERT INTO grade_components 
        (subject_id, component_type, component_name, max_score, weight_percentage, display_order)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (subject_id, component_type, component_name, max_score, weight_percentage, display_order))


def get_grade_components_by_subject(subject_id):
    """Get all grade components for a subject, ordered by display_order"""
    query = """
        SELECT * FROM grade_components
        WHERE subject_id = %s
        ORDER BY display_order, component_type, id
    """
    return execute_query(query, (subject_id,), fetch_all=True)


def get_component_count_by_type(subject_id, component_type):
    """Get count of existing components of a specific type for auto-numbering"""
    query = """
        SELECT COUNT(*) as count
        FROM grade_components
        WHERE subject_id = %s AND component_type = %s
    """
    result = execute_query(query, (subject_id, component_type), fetch_one=True)
    return int(result['count']) if result else 0


def update_grade_component(component_id, component_type, component_name, max_score, weight_percentage, display_order):
    """Update an existing grade component"""
    query = """
        UPDATE grade_components
        SET component_type = %s,
            component_name = %s,
            max_score = %s,
            weight_percentage = %s,
            display_order = %s
        WHERE id = %s
        RETURNING id
    """
    return execute_insert_returning(query, (component_type, component_name, max_score, weight_percentage, display_order, component_id))


def delete_grade_component(component_id):
    """Delete a grade component"""
    query = "DELETE FROM grade_components WHERE id = %s RETURNING id"
    return execute_insert_returning(query, (component_id,))


def delete_grade_components_by_type(subject_id, component_type):
    """Delete all grade components of a specific type for a subject"""
    query = "DELETE FROM grade_components WHERE subject_id = %s AND component_type = %s RETURNING id"
    return execute_query(query, (subject_id, component_type), fetch_all=True)


def update_grade_components_by_type(subject_id, component_type, new_total_weight):
    """Update weight for all components of a type (redistribute equally)"""
    # Get all components of this type
    components = execute_query(
        "SELECT id, weight_percentage FROM grade_components WHERE subject_id = %s AND component_type = %s ORDER BY id",
        (subject_id, component_type),
        fetch_all=True
    )
    
    if not components:
        return False
    
    count = len(components)
    individual_weight = round(new_total_weight / count, 2)
    
    # Handle rounding
    weights = [individual_weight] * count
    if sum(weights) != new_total_weight:
        weights[-1] = round(new_total_weight - sum(weights[:-1]), 2)
    
    # Update each component
    for i, comp in enumerate(components):
        execute_query(
            "UPDATE grade_components SET weight_percentage = %s, max_score = %s WHERE id = %s",
            (weights[i], weights[i], comp['id']),
            fetch_one=False
        )
    
    return True


def get_subject_total_weight(subject_id):
    """Calculate total weight percentage for a subject's grade components"""
    query = """
        SELECT COALESCE(SUM(weight_percentage), 0) as total_weight
        FROM grade_components
        WHERE subject_id = %s
    """
    result = execute_query(query, (subject_id,), fetch_one=True)
    return float(result['total_weight']) if result else 0.0


def get_grade_components_summary(subject_id):
    """Get grade components grouped by type with counts"""
    query = """
        SELECT 
            component_type,
            COUNT(*) as count,
            SUM(weight_percentage) as total_weight
        FROM grade_components
        WHERE subject_id = %s
        GROUP BY component_type
        ORDER BY component_type
    """
    return execute_query(query, (subject_id,), fetch_all=True)


def update_component_display_order(component_id, new_order):
    """Update the display order of a single grade component"""
    query = """
        UPDATE grade_components
        SET display_order = %s
        WHERE id = %s
    """
    try:
        execute_query(query, (new_order, component_id))
        return True
    except Exception as e:
        print(f"Error updating display order: {e}")
        return False


def reorder_categories_by_type(subject_id, category_order_list):
    """
    Reorder all components by category position
    category_order_list: list of component_types in desired order
    Each category gets a base order (0, 100, 200...), components within are sequential
    """
    try:
        print(f"Reordering categories for subject {subject_id}")
        print(f"New order: {category_order_list}")
        
        for idx, component_type in enumerate(category_order_list):
            base_order = idx * 100
            print(f"Processing category {component_type} at position {idx} (base_order={base_order})")
            
            # Get all components of this type, ordered by current display_order
            query_get = """
                SELECT id, component_name, display_order FROM grade_components
                WHERE subject_id = %s AND component_type = %s
                ORDER BY display_order, id
            """
            components = execute_query(query_get, (subject_id, component_type), fetch_all=True)
            print(f"  Found {len(components) if components else 0} components")
            
            if components:
                # Update each component with sequential ordering
                for i, comp in enumerate(components):
                    new_order = base_order + i
                    old_order = comp['display_order']
                    print(f"    Updating {comp['component_name']}: {old_order} -> {new_order}")
                    query_update = """
                        UPDATE grade_components
                        SET display_order = %s
                        WHERE id = %s
                    """
                    result = execute_query(query_update, (new_order, comp['id']))
                    print(f"      Update result: {result}")
        
        print("Reordering complete!")
        return True
    except Exception as e:
        print(f"Error reordering categories: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================
# WEEKLY TOPICS QUERIES
# =============================================

def create_weekly_topic(class_id, subject_id, teacher_id, week_number, topic, description=None, date_covered=None):
    """Create a weekly topic"""
    query = """
        INSERT INTO weekly_topics (class_id, subject_id, teacher_id, week_number, topic, description, date_covered)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (class_id, subject_id, week_number) 
        DO UPDATE SET topic = EXCLUDED.topic, description = EXCLUDED.description, date_covered = EXCLUDED.date_covered
        RETURNING id
    """
    return execute_insert_returning(query, (class_id, subject_id, teacher_id, week_number, topic, description, date_covered))


def get_weekly_topics_by_class(class_id):
    """Get all weekly topics for a class"""
    query = """
        SELECT wt.*, s.name as subject_name, u.full_name as teacher_name
        FROM weekly_topics wt
        JOIN subjects s ON wt.subject_id = s.id
        LEFT JOIN teachers t ON wt.teacher_id = t.id
        LEFT JOIN users u ON t.user_id = u.id
        WHERE wt.class_id = %s
        ORDER BY s.name, wt.week_number
    """
    return execute_query(query, (class_id,), fetch_all=True)


def get_weekly_topics_by_subject(subject_id):
    """Get weekly topics for a subject"""
    query = """
        SELECT wt.*, u.full_name as teacher_name
        FROM weekly_topics wt
        LEFT JOIN teachers t ON wt.teacher_id = t.id
        LEFT JOIN users u ON t.user_id = u.id
        WHERE wt.subject_id = %s
        ORDER BY wt.week_number
    """
    return execute_query(query, (subject_id,), fetch_all=True)


# =============================================
# TIMETABLE QUERIES
# =============================================

def create_timetable_entry(class_id, subject_id, teacher_id, day_of_week, start_time, end_time, room=None):
    """Create a timetable entry"""
    query = """
        INSERT INTO timetable (class_id, subject_id, teacher_id, day_of_week, start_time, end_time, room)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (class_id, subject_id, teacher_id, day_of_week, start_time, end_time, room))


def get_timetable_by_class(class_id):
    """Get timetable for a class"""
    query = """
        SELECT tt.*, s.name as subject_name, u.full_name as teacher_name
        FROM timetable tt
        JOIN subjects s ON tt.subject_id = s.id
        LEFT JOIN teachers t ON tt.teacher_id = t.id
        LEFT JOIN users u ON t.user_id = u.id
        WHERE tt.class_id = %s
        ORDER BY 
            CASE tt.day_of_week
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
                WHEN 'Sunday' THEN 7
            END,
            tt.start_time
    """
    return execute_query(query, (class_id,), fetch_all=True)


def get_timetable_by_teacher(teacher_id):
    """Get timetable for a teacher"""
    query = """
        SELECT tt.*, s.name as subject_name, c.name as class_name
        FROM timetable tt
        JOIN subjects s ON tt.subject_id = s.id
        JOIN classes c ON tt.class_id = c.id
        WHERE tt.teacher_id = %s
        ORDER BY 
            CASE tt.day_of_week
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
                WHEN 'Sunday' THEN 7
            END,
            tt.start_time
    """
    return execute_query(query, (teacher_id,), fetch_all=True)


# =============================================
# LECTURE FILES MANAGEMENT
# =============================================

def create_lecture_file(subject_id, teacher_id, class_id, title, description, file_name, file_path, file_size, file_type, week_number=None):
    """Upload a new lecture file"""
    query = """
        INSERT INTO lecture_files (subject_id, teacher_id, class_id, title, description, file_name, file_path, file_size, file_type, week_number)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (subject_id, teacher_id, class_id, title, description, file_name, file_path, file_size, file_type, week_number))


def get_lecture_files_by_subject(subject_id):
    """Get all lecture files for a subject"""
    query = """
        SELECT lf.*, u.full_name as teacher_name
        FROM lecture_files lf
        JOIN teachers t ON lf.teacher_id = t.id
        JOIN users u ON t.user_id = u.id
        WHERE lf.subject_id = %s
        ORDER BY lf.week_number NULLS LAST, lf.uploaded_at DESC
    """
    return execute_query(query, (subject_id,), fetch_all=True)


def get_lecture_files_by_teacher(teacher_id):
    """Get all lecture files uploaded by a teacher"""
    query = """
        SELECT lf.*, s.name as subject_name, c.name as class_name
        FROM lecture_files lf
        JOIN subjects s ON lf.subject_id = s.id
        LEFT JOIN classes c ON lf.class_id = c.id
        WHERE lf.teacher_id = %s
        ORDER BY lf.uploaded_at DESC
    """
    return execute_query(query, (teacher_id,), fetch_all=True)


def get_lecture_files_by_class(class_id):
    """Get all lecture files for a class"""
    query = """
        SELECT lf.*, s.name as subject_name, u.full_name as teacher_name
        FROM lecture_files lf
        JOIN subjects s ON lf.subject_id = s.id
        JOIN teachers t ON lf.teacher_id = t.id
        JOIN users u ON t.user_id = u.id
        WHERE lf.class_id = %s
        ORDER BY s.name, lf.week_number NULLS LAST, lf.uploaded_at DESC
    """
    return execute_query(query, (class_id,), fetch_all=True)


def get_lecture_file_by_id(file_id):
    """Get a specific lecture file"""
    query = """
        SELECT lf.*, s.name as subject_name, u.full_name as teacher_name
        FROM lecture_files lf
        JOIN subjects s ON lf.subject_id = s.id
        JOIN teachers t ON lf.teacher_id = t.id
        JOIN users u ON t.user_id = u.id
        WHERE lf.id = %s
    """
    return execute_query(query, (file_id,), fetch_one=True)


def delete_lecture_file(file_id):
    """Delete a lecture file"""
    query = "DELETE FROM lecture_files WHERE id = %s"
    return execute_query(query, (file_id,))


# =============================================
# SEMESTER SUBJECTS QUERIES (NEW STRUCTURE)
# =============================================

def get_all_semester_subjects():
    """Get all semester subjects"""
    query = """
        SELECT * FROM semester_subjects
        ORDER BY year, semester, name
    """
    return execute_query(query, fetch_all=True)


def get_semester_subjects(year, semester):
    """Get subjects for a specific year and semester"""
    query = """
        SELECT * FROM semester_subjects
        WHERE year = %s AND semester = %s
        ORDER BY name
    """
    return execute_query(query, (year, semester), fetch_all=True)


def get_semester_subject_by_id(subject_id):
    """Get a semester subject by ID"""
    query = "SELECT * FROM semester_subjects WHERE id = %s"
    return execute_query(query, (subject_id,), fetch_one=True)


def create_semester_subject(name, year, semester, description=None):
    """Create a new semester subject"""
    query = """
        INSERT INTO semester_subjects (name, year, semester, description)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (name, year, semester, description))


# =============================================
# TEACHER ASSIGNMENTS (NEW STRUCTURE)
# =============================================

def get_teacher_assignments(teacher_id):
    """Get all subject assignments for a teacher"""
    query = """
        SELECT ta.*, ss.name as subject_name, ss.year, ss.semester
        FROM teacher_assignments ta
        JOIN semester_subjects ss ON ta.subject_id = ss.id
        WHERE ta.teacher_id = %s
        ORDER BY ss.year, ss.semester, ta.shift
    """
    return execute_query(query, (teacher_id,), fetch_all=True)


def assign_teacher_to_subject(teacher_id, subject_id, class_id):
    """Assign a teacher to teach a subject for a specific class"""
    # Get shift from class
    class_info = execute_query(
        "SELECT shift FROM classes WHERE id = %s",
        (class_id,),
        fetch_one=True
    )
    if not class_info:
        return None
    
    query = """
        INSERT INTO teacher_assignments (teacher_id, subject_id, class_id, shift)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        RETURNING id
    """
    return execute_insert_returning(query, (teacher_id, subject_id, class_id, class_info['shift']))


def remove_teacher_assignment(assignment_id):
    """Remove a teacher assignment"""
    query = "DELETE FROM teacher_assignments WHERE id = %s"
    return execute_query(query, (assignment_id,))


def get_teachers_for_subject(subject_id, class_id=None):
    """Get all teachers assigned to a subject"""
    query = """
        SELECT ta.*, t.id as teacher_id, u.full_name as teacher_name,
               c.year, c.semester, c.section, c.shift
        FROM teacher_assignments ta
        JOIN teachers t ON ta.teacher_id = t.id
        JOIN users u ON t.user_id = u.id
        JOIN classes c ON ta.class_id = c.id
        WHERE ta.subject_id = %s
    """
    params = [subject_id]
    if class_id:
        query += " AND ta.class_id = %s"
        params.append(class_id)
    query += " ORDER BY c.semester, c.section"
    return execute_query(query, tuple(params), fetch_all=True)


# =============================================
# STUDENT QUERIES (UPDATED FOR NEW STRUCTURE)
# =============================================

def create_student_v2(user_id, year, shift, section=None, student_number=None, phone=None):
    """Create student with year/shift (section assigned later)"""
    query = """
        INSERT INTO students (user_id, year, shift, section, student_number, phone)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (user_id, year, shift, section, student_number, phone))


def update_student_v2(student_id, full_name, email, year, semester, shift, section, student_number, phone):
    """Update student with new structure including semester"""
    query = """
        UPDATE students 
        SET year = %s, semester = %s, shift = %s, section = %s, student_number = %s, phone = %s
        WHERE id = %s
    """
    result = execute_query(query, (year, semester, shift, section, student_number, phone, student_id))
    
    # Also update user info
    student = get_student_by_id(student_id)
    if student:
        query2 = "UPDATE users SET full_name = %s, email = %s WHERE id = %s"
        execute_query(query2, (full_name, email, student['user_id']))
    
    return result


def get_students_by_year_shift(year, shift, section=None):
    """Get students by year and shift, optionally filtered by section"""
    query = """
        SELECT s.*, u.full_name, u.username, u.email
        FROM students s
        JOIN users u ON s.user_id = u.id
        WHERE s.year = %s AND s.shift = %s
    """
    params = [year, shift]
    if section:
        query += " AND s.section = %s"
        params.append(section)
    query += " ORDER BY s.section, u.full_name"
    return execute_query(query, tuple(params), fetch_all=True)


def get_students_without_section(year=None, shift=None):
    """Get students not yet assigned to a section"""
    query = """
        SELECT s.*, u.full_name, u.username, u.email
        FROM students s
        JOIN users u ON s.user_id = u.id
        WHERE s.section IS NULL
    """
    params = []
    if year:
        query += " AND s.year = %s"
        params.append(year)
    if shift:
        query += " AND s.shift = %s"
        params.append(shift)
    query += " ORDER BY s.year, s.shift, u.full_name"
    return execute_query(query, tuple(params) if params else None, fetch_all=True)


def assign_student_section(student_id, section):
    """Assign a student to a section"""
    query = "UPDATE students SET section = %s WHERE id = %s"
    return execute_query(query, (section, student_id))


def update_student_v2(student_id, full_name, email, year, semester, shift, section, student_number, phone):
    """Update student with new year/semester/shift/section structure"""
    # Update student record
    query = """
        UPDATE students 
        SET year = %s, semester = %s, shift = %s, section = %s, student_number = %s, phone = %s
        WHERE id = %s
    """
    result = execute_query(query, (year, semester, shift, section, student_number, phone, student_id))
    
    # Also update user info
    student = get_student_by_id(student_id)
    if student:
        query2 = "UPDATE users SET full_name = %s, email = %s WHERE id = %s"
        execute_query(query2, (full_name, email, student['user_id']))
    
    return result


def get_all_students_v2():
    """Get all students with new structure fields"""
    query = """
        SELECT s.*, u.full_name, u.username, u.email
        FROM students s
        JOIN users u ON s.user_id = u.id
        ORDER BY s.year, s.shift, s.section, u.full_name
    """
    return execute_query(query, fetch_all=True)


def get_student_by_id_v2(student_id):
    """Get student by ID with new structure"""
    query = """
        SELECT s.*, u.full_name, u.username, u.email
        FROM students s
        JOIN users u ON s.user_id = u.id
        WHERE s.id = %s
    """
    return execute_query(query, (student_id,), fetch_one=True)


# =============================================
# TEACHER VIEW HELPERS
# =============================================

def get_teacher_sections(teacher_id, year, semester, shift):
    """Get all sections a teacher teaches for a year/semester/shift"""
    # Get distinct sections where students exist
    query = """
        SELECT DISTINCT s.section
        FROM students s
        WHERE s.year = %s AND s.shift = %s AND s.section IS NOT NULL
        ORDER BY s.section
    """
    # For year 1, semester is 1 or 2; for year 2, semester is 3 or 4
    return execute_query(query, (year, shift), fetch_all=True)


def get_teacher_current_context(teacher_id):
    """Get teacher's assigned subjects grouped by year/shift"""
    query = """
        SELECT ta.shift, ss.year, ss.semester, ss.id as subject_id, ss.name as subject_name,
               (SELECT COUNT(DISTINCT s.section) FROM students s 
                WHERE s.year = ss.year AND s.shift = ta.shift AND s.section IS NOT NULL) as section_count
        FROM teacher_assignments ta
        JOIN semester_subjects ss ON ta.subject_id = ss.id
        WHERE ta.teacher_id = %s
        ORDER BY ss.year, ss.semester, ta.shift, ss.name
    """
    return execute_query(query, (teacher_id,), fetch_all=True)


# =============================================
# CLASS SCHEDULE QUERIES
# =============================================

def get_schedule(semester, shift, section):
    """Get schedule for a specific semester/shift/section"""
    query = """
        SELECT * FROM class_schedules
        WHERE semester = %s AND shift = %s AND section = %s
    """
    return execute_query(query, (semester, shift, section), fetch_one=True)


def get_class_schedule_data(semester, shift, section):
    """Get parsed schedule data for a specific class (for student view)"""
    import json
    
    schedule = get_schedule(semester, shift, section)
    if not schedule or not schedule.get('schedule_data'):
        return None
    
    data = schedule['schedule_data']
    if isinstance(data, str):
        data = json.loads(data)
    
    return data


def get_teacher_schedule_from_builder(teacher_name):
    """Get a teacher's schedule entries from the class_schedules builder data.
    Searches all saved schedules for entries matching this teacher name."""
    import json
    
    query = """
        SELECT semester, shift, section, schedule_data 
        FROM class_schedules 
        WHERE schedule_data IS NOT NULL
    """
    rows = execute_query(query, fetch_all=True)
    if not rows:
        return []
    
    day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
    teacher_entries = []
    teacher_lower = teacher_name.lower().strip()
    
    for row in rows:
        data = row['schedule_data']
        if isinstance(data, str):
            data = json.loads(data)
        if not data:
            continue
            
        for entry in data:
            if entry.get('isBreak'):
                continue
            # Check if teacher matches in theory or practical teacher fields
            entry_teacher = (entry.get('teacher') or '').lower().strip()
            practical_teacher = (entry.get('practicalTeacher') or '').lower().strip()
            
            if teacher_lower in (entry_teacher, practical_teacher) or \
               entry_teacher == teacher_lower or practical_teacher == teacher_lower:
                col = entry.get('col', 0)
                day = day_names[col] if col < len(day_names) else f'Day {col}'
                
                # Determine time based on lecture type
                lecture_type = entry.get('lectureType', 'theory')
                if lecture_type == 'practical':
                    start_time = entry.get('practicalStartTime') or entry.get('startTime', '')
                    end_time = entry.get('practicalEndTime') or entry.get('endTime', '')
                else:
                    start_time = entry.get('theoryStartTime') or entry.get('startTime', '')
                    end_time = entry.get('theoryEndTime') or entry.get('endTime', '')
                
                teacher_entries.append({
                    'day_of_week': day,
                    'start_time': start_time,
                    'end_time': end_time,
                    'subject_name': entry.get('subject', ''),
                    'lecture_type': lecture_type,
                    'room': entry.get('room', ''),
                    'semester': row['semester'],
                    'shift': row['shift'],
                    'section': row['section'],
                    'class_label': f"Sem {row['semester']} - {row['shift'].title()} - Class {row['section']}"
                })
    
    # Sort by day order, then start_time
    day_order = {d: i for i, d in enumerate(day_names)}
    teacher_entries.sort(key=lambda x: (day_order.get(x['day_of_week'], 99), x['start_time']))
    
    return teacher_entries


def save_schedule(semester, shift, section, schedule_data):
    """Save or update schedule for a semester/shift/section"""
    import json
    # Convert to JSON string if needed
    if isinstance(schedule_data, (list, dict)):
        schedule_data = json.dumps(schedule_data)
    
    query = """
        INSERT INTO class_schedules (semester, shift, section, schedule_data, updated_at)
        VALUES (%s, %s, %s, %s::jsonb, CURRENT_TIMESTAMP)
        ON CONFLICT (semester, shift, section)
        DO UPDATE SET schedule_data = EXCLUDED.schedule_data, updated_at = CURRENT_TIMESTAMP
        RETURNING id
    """
    return execute_insert_returning(query, (semester, shift, section, schedule_data))


def delete_schedule(semester, shift, section):
    """Delete a schedule"""
    query = """
        DELETE FROM class_schedules
        WHERE semester = %s AND shift = %s AND section = %s
    """
    return execute_query(query, (semester, shift, section))


def get_all_schedules():
    """Get all schedules"""
    query = """
        SELECT * FROM class_schedules
        ORDER BY semester, shift, section
    """
    return execute_query(query, fetch_all=True)


