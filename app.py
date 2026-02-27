"""
MIS Institute Management System
Main Flask Application
"""
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, date
import os
import db
from config import config

# Initialize Flask app
app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# File Upload Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'zip', 'rar', 'jpg', 'jpeg', 'png', 'gif'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =============================================
# AUTHENTICATION DECORATORS
# =============================================

def login_required(f):
    """Decorator to require login for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def teacher_required(f):
    """Decorator to require teacher role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') not in ['admin', 'teacher']:
            flash('Access denied. Teacher privileges required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# =============================================
# CONTEXT PROCESSORS
# =============================================

@app.context_processor
def inject_user():
    """Make user info available to all templates"""
    from datetime import datetime
    context = {'now': datetime.now}
    if 'user_id' in session:
        context['current_user'] = {
            'id': session.get('user_id'),
            'username': session.get('username'),
            'full_name': session.get('full_name'),
            'role': session.get('role')
        }
    else:
        context['current_user'] = None
    return context


# =============================================
# TEMPLATE FILTERS
# =============================================

@app.template_filter('replace_section')
def replace_section_filter(text):
    """Replace 'Section' with 'Class' and fix UTF-8 double-encoding artifacts"""
    if text:
        text = text.replace('Section', 'Class')
        # Fix common UTF-8 double-encoding artifacts
        text = text.replace('\u00c2\u00b7', '\u00b7')  # Â· -> middot
        text = text.replace('\u00e2\u0080\u0093', '\u2013')  # en-dash
        text = text.replace('\u00e2\u0080\u0094', '\u2014')  # em-dash
        text = text.replace('\u00c2\u00a0', ' ')  # non-breaking space
    return text


# =============================================
# AUTHENTICATION ROUTES
# =============================================

@app.route('/')
def index():
    """Home page - redirect to dashboard if logged in"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Please enter both email and password.', 'warning')
            return render_template('login.html')
        
        user = db.get_user_by_email(email)
        
        if user and (check_password_hash(user['password_hash'], password) or (user.get('plain_password') and user['plain_password'] == password)):
            # Set session variables
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            
            flash(f'Welcome back, {user["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# =============================================
# DASHBOARD ROUTES
# =============================================

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard - redirects based on role"""
    role = session.get('role')
    
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    elif role == 'student':
        return redirect(url_for('student_dashboard'))
    
    return render_template('dashboard.html')


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard with semester statistics"""
    users = db.get_all_users() or []
    teachers = db.get_all_teachers() or []
    
    # Get total student count directly from students table
    conn = db.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM students")
    row = cur.fetchone()
    total_students = row[0] if row else 0
    
    # Get total unique subject count
    cur.execute("SELECT COUNT(DISTINCT name) FROM subjects")
    row = cur.fetchone()
    total_subjects = row[0] if row else 0
    cur.close()
    conn.close()
    
    # Get student counts per semester
    semester_stats = db.get_student_counts_by_semester()
    
    stats = {
        'total_users': len(users),
        'total_teachers': len(teachers),
        'total_students': total_students,
        'total_subjects': total_subjects,
        'semesters': semester_stats
    }
    
    return render_template('admin/dashboard.html', stats=stats)


@app.route('/teacher/dashboard')
@teacher_required
def teacher_dashboard():
    """Teacher dashboard"""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    homework = db.get_homework_by_teacher(teacher['id']) or []
    
    # Group subjects by name for cleaner display
    grouped_subjects = {}
    for s in subjects:
        name = s['name']
        if name not in grouped_subjects:
            grouped_subjects[name] = {'count': 0, 'classes': [], 'credits': s.get('credits', 6)}
        grouped_subjects[name]['count'] += 1
        grouped_subjects[name]['classes'].append({
            'section': s.get('section', ''),
            'semester': s.get('semester', ''),
            'shift': s.get('shift', 'morning'),
        })
    
    return render_template('teacher/dashboard.html', 
                         teacher=teacher,
                         subjects=subjects,
                         grouped_subjects=grouped_subjects,
                         homework=homework)


@app.route('/student/dashboard')
@login_required
def student_dashboard():
    """Student dashboard"""
    from datetime import date
    if session.get('role') != 'student':
        return redirect(url_for('dashboard'))
    
    student = db.get_student_by_user_id(session['user_id'])
    
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    grades = db.get_grades_by_student(student['id']) or []
    
    homework = []
    weekly_topics = []
    schedule_data = None
    current_semester = None
    
    if student['class_id']:
        homework = db.get_homework_by_class(student['class_id']) or []
        weekly_topics = db.get_weekly_topics_by_class(student['class_id']) or []

        # Use students table as the single source of truth for semester/shift/section.
        # classes.semester can diverge from students.semester when admin reassigns a student;
        # update_student() now syncs them, but use students table here to stay consistent
        # with the admin view which also reads from the students table (get_all_students_v2).
        if student.get('semester'):
            current_semester = student['semester']
            schedule_data = db.get_class_schedule_data(
                student['semester'],
                student['shift'],
                student['section']
            )
    
    # Filter attendance by current semester so promoted students only see current data
    attendance = db.get_attendance_by_student(student['id'], semester=current_semester) or []
    
    today = date.today().isoformat()
    return render_template('student/dashboard.html',
                         student=student,
                         attendance=attendance,
                         grades=grades,
                         homework=homework,
                         weekly_topics=weekly_topics,
                         schedule_data=schedule_data,
                         today=today)


@app.route('/student/subjects')
@login_required
def student_subjects():
    """Student subjects - view and enroll"""
    if session.get('role') != 'student':
        return redirect(url_for('dashboard'))
    
    student = db.get_student_by_user_id(session['user_id'])
    
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get class info to show semester
    class_info = None
    semester = None
    if student['class_id']:
        class_info = db.execute_query(
            'SELECT year, semester, section, shift FROM classes WHERE id = %s', 
            (student['class_id'],), 
            fetch_one=True
        )
        if class_info:
            semester = class_info['semester']
    
    # Check if enrollment is active for this semester
    enrollment_period = None
    enrollment_active = False
    if semester:
        enrollment_period = db.get_active_enrollment_period(semester)
        enrollment_active = enrollment_period is not None
    
    # Get available subjects for student's semester
    subjects = db.get_available_subjects_for_student(student['id']) or []
    
    return render_template('student/subjects.html',
                         student=student,
                         class_info=class_info,
                         subjects=subjects,
                         enrollment_period=enrollment_period,
                         enrollment_active=enrollment_active)


@app.route('/student/subjects/enroll/<int:subject_id>', methods=['POST'])
@login_required
def student_enroll_subject(subject_id):
    """Enroll in a subject"""
    if session.get('role') != 'student':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    student = db.get_student_by_user_id(session['user_id'])
    if not student:
        return jsonify({'success': False, 'error': 'Student profile not found'}), 404
    
    # Check enrollment period
    class_info = db.execute_query(
        'SELECT semester FROM classes WHERE id = %s', 
        (student['class_id'],), 
        fetch_one=True
    )
    if class_info:
        semester = class_info['semester']
        if not db.is_enrollment_active(semester):
            return jsonify({'success': False, 'error': 'Enrollment period has ended or not started yet'}), 403
    
    try:
        # Check if subject exists
        subject = db.execute_query("SELECT id, name FROM subjects WHERE id = %s", (subject_id,), fetch_one=True)
        if not subject:
            return jsonify({'success': False, 'error': 'Subject not found'}), 404
        
        success = db.enroll_student_in_subject(student['id'], subject_id)
        if success:
            return jsonify({'success': True, 'message': 'Enrolled successfully'})
        else:
            return jsonify({'success': False, 'error': 'Already enrolled'})
    except Exception as e:
        print(f"Error enrolling student {student['id']} in subject {subject_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/student/subjects/unenroll/<int:subject_id>', methods=['POST'])
@login_required
def student_unenroll_subject(subject_id):
    """Unenroll from a subject"""
    if session.get('role') != 'student':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    student = db.get_student_by_user_id(session['user_id'])
    if not student:
        return jsonify({'success': False, 'error': 'Student profile not found'}), 404
    
    # Check enrollment period
    class_info = db.execute_query(
        'SELECT semester FROM classes WHERE id = %s', 
        (student['class_id'],), 
        fetch_one=True
    )
    if class_info:
        semester = class_info['semester']
        if not db.is_enrollment_active(semester):
            return jsonify({'success': False, 'error': 'Enrollment period has ended or not started yet'}), 403
    
    try:
        db.unenroll_student_from_subject(student['id'], subject_id)
        return jsonify({'success': True, 'message': 'Unenrolled successfully'})
    except Exception as e:
        print(f"Error unenrolling student {student['id']} from subject {subject_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/student/grades')
@login_required
def student_grades():
    """View student grades"""
    if session.get('role') != 'student':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard'))
    
    student = db.get_student_by_user_id(session['user_id'])
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get all enrolled subjects (across all semesters)
    all_enrolled = db.get_enrolled_subjects_for_student(student['id']) or []
    
    # Build a list of distinct semesters the student has subjects in
    semester_set = set()
    for subj in all_enrolled:
        if subj.get('semester'):
            semester_set.add(subj['semester'])
    available_semesters = sorted(semester_set)
    
    # Current student semester (default view)
    current_semester = student.get('semester') or (max(available_semesters) if available_semesters else 1)
    
    # Selected semester from query param (defaults to current)
    selected_semester = request.args.get('semester', type=int) or current_semester
    
    # Filter subjects to only the selected semester
    enrolled_subjects = [s for s in all_enrolled if s.get('semester') == selected_semester]
    
    # Get selected subject from query parameter
    selected_subject_id = request.args.get('subject_id', type=int)
    
    grades_data = []
    subject_info = None
    total_score = 0
    total_max = 0
    
    if selected_subject_id:
        # Verify the selected subject is in the filtered list
        if any(s['id'] == selected_subject_id for s in enrolled_subjects):
            grades_data = db.get_student_grades_for_subject(student['id'], selected_subject_id) or []
            subject_info = next((s for s in enrolled_subjects if s['id'] == selected_subject_id), None)
            for grade in grades_data:
                if grade.get('score') is not None:
                    total_score += float(grade['score'])
                total_max += float(grade['max_score'])
        else:
            # Subject not in selected semester, reset
            selected_subject_id = None
    
    return render_template('student/grades.html', 
                         enrolled_subjects=enrolled_subjects,
                         selected_subject_id=selected_subject_id,
                         subject_info=subject_info,
                         grades_data=grades_data,
                         total_score=total_score,
                         total_max=total_max,
                         student=student,
                         available_semesters=available_semesters,
                         selected_semester=selected_semester,
                         current_semester=current_semester)


@app.route('/student/results')
@login_required
def student_results():
    """View student final results/transcript — grouped by semester"""
    if session.get('role') != 'student':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard'))
    
    student = db.get_student_by_user_id(session['user_id'])
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Types where sub-components are SUMMED (not averaged)
    sum_types = ['midterm', 'final']
    
    # Get all enrolled subjects (across all semesters)
    enrolled_subjects = db.get_enrolled_subjects_for_student(student['id']) or []
    
    grades_exist = False
    
    # Group subjects by semester
    subjects_by_semester = {}
    for subj in enrolled_subjects:
        sem = subj.get('semester') or 0
        if sem not in subjects_by_semester:
            subjects_by_semester[sem] = []
        subjects_by_semester[sem].append(subj)
    
    # Build semester_results: list of {semester, year, results[], totals}
    semester_results = []
    grand_total_credits = 0
    grand_total_weighted = 0
    
    for sem in sorted(subjects_by_semester.keys()):
        if sem == 0:
            continue
        
        sem_subjects = subjects_by_semester[sem]
        results = []
        sem_credits_possible = 0
        sem_credits_earned = 0
        sem_has_published = False
        
        for subject in sem_subjects:
            grades_data = db.get_student_grades_for_subject(student['id'], subject['id']) or []
            if not grades_data:
                continue
            grades_exist = True
            
            if not subject.get('results_published'):
                continue
            
            sem_has_published = True
            
            # Group by component type
            grouped = {}
            for grade in grades_data:
                type_key = grade['component_type']
                if type_key not in grouped:
                    grouped[type_key] = []
                grouped[type_key].append(grade)
            
            # Calculate total using sum_types logic
            total_score = 0
            total_max = 0
            
            for component_type, group_grades in grouped.items():
                group_total_score = sum(float(g['score'] or 0) for g in group_grades)
                group_total_max = sum(float(g['max_score']) for g in group_grades)
                group_count = len(group_grades)
                
                if component_type in sum_types:
                    total_score += group_total_score
                    total_max += group_total_max
                elif group_count > 0:
                    total_score += group_total_score / group_count
                    total_max += group_total_max / group_count
            
            percentage = (total_score / total_max * 100) if total_max > 0 else 0
            
            # Letter grade
            if percentage >= 97: letter_grade = 'A+'
            elif percentage >= 93: letter_grade = 'A'
            elif percentage >= 90: letter_grade = 'A-'
            elif percentage >= 87: letter_grade = 'B+'
            elif percentage >= 83: letter_grade = 'B'
            elif percentage >= 80: letter_grade = 'B-'
            elif percentage >= 77: letter_grade = 'C+'
            elif percentage >= 73: letter_grade = 'C'
            elif percentage >= 70: letter_grade = 'C-'
            elif percentage >= 67: letter_grade = 'D+'
            elif percentage >= 63: letter_grade = 'D'
            elif percentage >= 60: letter_grade = 'D-'
            else: letter_grade = 'F'
            
            passed = percentage >= 60
            credits = subject.get('credits') or 0
            weighted_score = round(percentage * credits / 100, 3)
            
            results.append({
                'subject_name': subject['name'],
                'credits': credits,
                'percentage': round(percentage, 1),
                'letter_grade': letter_grade,
                'weighted_score': weighted_score,
                'passed': passed
            })
            
            sem_credits_possible += credits
            if passed:
                sem_credits_earned += credits
        
        if sem_has_published and results:
            sem_weighted = round(sum(r['weighted_score'] for r in results), 3)
            year = 1 if sem <= 2 else 2
            semester_results.append({
                'semester': sem,
                'year': year,
                'results': results,
                'total_weighted_score': sem_weighted,
                'credits_possible': sem_credits_possible,
                'credits_earned': sem_credits_earned
            })
            grand_total_credits += sem_credits_possible
            grand_total_weighted += sem_weighted
    
    return render_template('student/results.html', 
                         student=student,
                         semester_results=semester_results,
                         grades_exist=grades_exist,
                         grand_total_weighted=round(grand_total_weighted, 3),
                         grand_total_credits=grand_total_credits)


# =============================================
# ADMIN - ATTENDANCE RECORDS
# =============================================

@app.route('/admin/attendance-records')
@admin_required
def admin_attendance_records():
    """View all attendance records submitted by teachers"""
    conn = db.get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get attendance submissions grouped by date, subject, teacher with class info
        cur.execute("""
            SELECT 
                a.date,
                s.id,
                s.name,
                c.id,
                c.name,
                c.shift,
                c.semester,
                c.year,
                c.section,
                a.teacher_id,
                u.full_name,
                COUNT(a.id),
                SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END),
                SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END),
                SUM(CASE WHEN a.status = 'late' THEN 1 ELSE 0 END),
                SUM(CASE WHEN a.status = 'excused' THEN 1 ELSE 0 END),
                MAX(a.created_at)
            FROM attendance a
            JOIN subjects s ON a.subject_id = s.id
            JOIN students st ON a.student_id = st.id
            JOIN classes c ON st.class_id = c.id
            LEFT JOIN teachers t ON a.teacher_id = t.id
            LEFT JOIN users u ON t.user_id = u.id
            GROUP BY a.date, s.id, s.name, c.id, c.name, c.shift, c.semester, c.year, c.section, a.teacher_id, u.full_name
            ORDER BY a.date DESC, s.name
        """)
        rows = cur.fetchall()
        
        # Convert rows to dictionaries manually
        submissions = []
        for row in rows:
            submissions.append({
                'date': row[0],
                'subject_id': row[1],
                'subject_name': row[2],
                'class_id': row[3],
                'class_name': row[4],
                'shift': row[5],
                'semester': row[6],
                'year': row[7],
                'section': row[8],
                'teacher_id': row[9],
                'teacher_name': row[10],
                'total_records': row[11],
                'present_count': row[12],
                'absent_count': row[13],
                'late_count': row[14],
                'excused_count': row[15],
                'submitted_at': row[16]
            })
        
        # For each submission, get the student details
        for submission in submissions:
            cur.execute("""
                SELECT 
                    st.id,
                    u.full_name,
                    a.status,
                    a.notes
                FROM attendance a
                JOIN students st ON a.student_id = st.id
                JOIN users u ON st.user_id = u.id
                WHERE a.date = %s 
                  AND a.subject_id = %s
                  AND a.teacher_id IS NOT DISTINCT FROM %s
                ORDER BY u.full_name
            """, (submission['date'], submission['subject_id'], submission['teacher_id']))
            
            student_rows = cur.fetchall()
            submission['students'] = []
            for row in student_rows:
                submission['students'].append({
                    'id': row[0],
                    'student_name': row[1],
                    'status': row[2],
                    'notes': row[3]
                })
        
        return render_template('admin/attendance_records.html', submissions=submissions)
        
    except Exception as e:
        flash(f'Error loading attendance records: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))
    finally:
        cur.close()
        conn.close()

# =============================================
# ADMIN - ATTENDANCE SUMMARY
# =============================================

@app.route('/admin/attendance-summary')
@admin_required
def admin_attendance_summary():
    """View all students with filters, select student to see their attendance by subject"""
    conn = db.get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get all unique semesters
        cur.execute("SELECT DISTINCT semester FROM classes WHERE semester IS NOT NULL ORDER BY semester")
        semester_rows = cur.fetchall()
        semesters = [row[0] for row in semester_rows]
        
        # Get all unique shifts
        cur.execute("SELECT DISTINCT shift FROM classes WHERE shift IS NOT NULL ORDER BY shift")
        shift_rows = cur.fetchall()
        shifts = [row[0] for row in shift_rows]
        
        # Get filter parameters
        selected_semester = request.args.get('semester', type=int)
        selected_shift = request.args.get('shift')
        selected_section = request.args.get('section')
        
        # Build query with filters
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
        params = []
        
        if selected_semester:
            query += " WHERE c.semester = %s"
            params.append(selected_semester)
            
            if selected_shift:
                query += " AND c.shift = %s"
                params.append(selected_shift)
                
            if selected_section:
                query += " AND c.section = %s"
                params.append(selected_section)
        elif selected_shift:
            query += " WHERE c.shift = %s"
            params.append(selected_shift)
            
            if selected_section:
                query += " AND c.section = %s"
                params.append(selected_section)
        elif selected_section:
            query += " WHERE c.section = %s"
            params.append(selected_section)
        
        query += " ORDER BY u.full_name"
        
        cur.execute(query, params)
        student_rows = cur.fetchall()
        
        # Manually map columns since no aliases
        students = []
        for row in student_rows:
            students.append({
                'student_id': row[0],
                'student_name': row[1],
                'student_number': row[2],
                'class_name': row[3],
                'semester': row[4],
                'section': row[5],
                'shift': row[6]
            })
        
        # Get sections for selected semester and shift
        sections = []
        if selected_semester or selected_shift:
            section_query = "SELECT DISTINCT section FROM classes"
            section_params = []
            
            if selected_semester and selected_shift:
                section_query += " WHERE semester = %s AND shift = %s"
                section_params.append(selected_semester)
                section_params.append(selected_shift)
            elif selected_semester:
                section_query += " WHERE semester = %s"
                section_params.append(selected_semester)
            elif selected_shift:
                section_query += " WHERE shift = %s"
                section_params.append(selected_shift)
                
            section_query += " ORDER BY section"
            cur.execute(section_query, section_params)
            section_rows = cur.fetchall()
            sections = [row[0] for row in section_rows]
        
        
        return render_template('admin/attendance_summary.html', 
                             students=students,
                             semesters=semesters,
                             shifts=shifts,
                             sections=sections,
                             selected_semester=selected_semester,
                             selected_shift=selected_shift,
                             selected_section=selected_section)
        
    except Exception as e:
        flash(f'Error loading students: {str(e)}', 'danger')
        return redirect(url_for('admin_attendance_records'))
    finally:
        cur.close()
        conn.close()

@app.route('/admin/api/subjects-by-semester/<int:semester>')
@admin_required
def api_subjects_by_semester(semester):
    """API endpoint to get subjects for a specific semester"""
    conn = db.get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT id, name, semester
            FROM subjects
            WHERE semester = %s
            ORDER BY name
        """, (semester,))
        
        subject_rows = cur.fetchall()
        subjects = [db.row_to_dict(cur, row) for row in subject_rows]
        
        return jsonify(subjects)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/admin/api/student-attendance/<int:student_id>/<subject_id>')
@admin_required
def api_student_attendance(student_id, subject_id):
    """API endpoint to get detailed attendance for a student in a specific subject or all subjects"""
    conn = db.get_db_connection()
    cur = conn.cursor()
    semester_filter = request.args.get('semester', type=int)
    
    try:
        # Check if requesting all subjects
        if subject_id == 'all':
            # Get attendance records for this student across all subjects
            if semester_filter:
                cur.execute("""
                    SELECT 
                        a.date,
                        a.status,
                        s.name,
                        t.full_name,
                        a.notes
                    FROM attendance a
                    JOIN subjects s ON a.subject_id = s.id
                    LEFT JOIN teachers te ON a.teacher_id = te.id
                    LEFT JOIN users t ON te.user_id = t.id
                    WHERE a.student_id = %s AND s.semester = %s
                    ORDER BY a.date DESC
                """, (student_id, semester_filter))
            else:
                cur.execute("""
                    SELECT 
                        a.date,
                        a.status,
                        s.name,
                        t.full_name,
                        a.notes
                    FROM attendance a
                    JOIN subjects s ON a.subject_id = s.id
                    LEFT JOIN teachers te ON a.teacher_id = te.id
                    LEFT JOIN users t ON te.user_id = t.id
                    WHERE a.student_id = %s
                    ORDER BY a.date DESC
                """, (student_id,))
            
            attendance_rows = cur.fetchall()
            attendance_records = []
            for row in attendance_rows:
                attendance_records.append({
                    'date': row[0],
                    'status': row[1],
                    'subject_name': row[2],
                    'teacher_name': row[3],
                    'notes': row[4]
                })
        else:
            # Get attendance records for this student in this subject
            cur.execute("""
                SELECT 
                    a.date,
                    a.status,
                    s.name,
                    t.full_name,
                    a.notes
                FROM attendance a
                JOIN subjects s ON a.subject_id = s.id
                LEFT JOIN teachers te ON a.teacher_id = te.id
                LEFT JOIN users t ON te.user_id = t.id
                WHERE a.student_id = %s AND a.subject_id = %s
                ORDER BY a.date DESC
            """, (student_id, int(subject_id)))
            
            attendance_rows = cur.fetchall()
            attendance_records = []
            for row in attendance_rows:
                attendance_records.append({
                    'date': row[0],
                    'status': row[1],
                    'subject_name': row[2],
                    'teacher_name': row[3],
                    'notes': row[4]
                })
        
        # Calculate summary statistics
        total = len(attendance_records)
        present = sum(1 for r in attendance_records if r['status'] == 'present')
        absent = sum(1 for r in attendance_records if r['status'] == 'absent')
        late = sum(1 for r in attendance_records if r['status'] == 'late')
        excused = sum(1 for r in attendance_records if r['status'] == 'excused')
        
        percentage = round((present / total) * 100, 1) if total > 0 else 0
        
        return jsonify({
            'records': attendance_records,
            'summary': {
                'total': total,
                'present': present,
                'absent': absent,
                'late': late,
                'excused': excused,
                'percentage': percentage
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# =============================================
# ADMIN - USER MANAGEMENT
# =============================================

@app.route('/admin/users')
@admin_required
def admin_users():
    """Manage users"""
    users = db.get_all_users() or []
    
    # Get extended data for smart filters
    teachers_raw = db.get_all_teachers_with_subjects() or []
    students_data = db.get_all_students_v2() or []
    
    # Enrich teacher data with subjects
    teachers_data = []
    for teacher in teachers_raw:
        teacher_id = teacher.get('teacher_id')
        subjects = db.get_subjects_by_teacher_id(teacher_id) or []
        teacher['subjects'] = subjects
        teachers_data.append(teacher)
    
    # Create lookup dictionaries
    teacher_lookup = {t['user_id']: t for t in teachers_data}
    student_lookup = {s['user_id']: s for s in students_data}
    
    return render_template('admin/users.html', 
                          users=users, 
                          teacher_lookup=teacher_lookup,
                          student_lookup=student_lookup)


@app.route('/admin/users/add', methods=['GET', 'POST'])
@admin_required
def admin_add_user():
    """Add new user"""
    classes = db.get_all_classes() or []
    default_role = request.args.get('role', '')  # Get role from URL parameter
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', '')
        email = request.form.get('email', '').strip()
        
        # Validation
        if not all([username, password, full_name, role]):
            flash('Please fill in all required fields.', 'warning')
            return render_template('admin/add_user.html', classes=classes)
        
        # Check if username exists
        if db.get_user_by_username(username):
            flash('Username already exists.', 'danger')
            return render_template('admin/add_user.html', classes=classes)
        
        # Create user
        password_hash = generate_password_hash(password)
        user_id = db.create_user(username, password_hash, full_name, role, email, password)
        
        if user_id:
            # Create role-specific profile
            if role == 'teacher':
                department = request.form.get('department', '').strip()
                phone = request.form.get('phone', '').strip()
                db.create_teacher(user_id, department, phone)
            elif role == 'student':
                class_id = request.form.get('class_id')
                student_number = request.form.get('student_number', '').strip()
                phone = request.form.get('phone', '').strip()
                db.create_student(user_id, class_id if class_id else None, student_number, phone)
            
            flash(f'User "{username}" created successfully!', 'success')
            return redirect(url_for('admin_users'))
        else:
            flash('Error creating user.', 'danger')
    
    return render_template('admin/add_user.html', classes=classes, default_role=default_role)


@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    """Delete a user"""
    if user_id == session['user_id']:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin_users'))
    
    result = db.delete_user(user_id)
    if result:
        flash('User deleted successfully.', 'success')
    else:
        flash('Error deleting user.', 'danger')
    
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/edit', methods=['POST'])
@admin_required
def admin_edit_user(user_id):
    """Edit user details"""
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    if not full_name:
        flash('Full name is required.', 'warning')
        return redirect(url_for('admin_users'))
    
    # Update basic info
    result = db.update_user(user_id, full_name, email)
    
    # Update password if provided
    if new_password:
        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('admin_users'))
        
        password_hash = generate_password_hash(new_password)
        db.update_user_password(user_id, password_hash)
    
    if result:
        flash('User updated successfully.', 'success')
    else:
        flash('Error updating user.', 'danger')
    
    return redirect(url_for('admin_users'))


# =============================================
# ADMIN - TEACHER MANAGEMENT
# =============================================

@app.route('/admin/teachers')
@admin_required
def admin_teachers():
    """View all teachers with their subjects"""
    teachers = db.get_all_teachers_with_subjects() or []
    classes = db.get_all_classes() or []
    unique_subjects = db.get_unique_subjects_by_semester() or []
    # Get subjects for each teacher
    for teacher in teachers:
        teacher['subjects'] = db.get_subjects_by_teacher_id(teacher['teacher_id']) or []
    return render_template('admin/teachers.html', teachers=teachers, classes=classes, unique_subjects=unique_subjects)


@app.route('/admin/teachers/<int:teacher_id>/assign-subject', methods=['POST'])
@admin_required
def admin_assign_subject_to_teacher(teacher_id):
    """Quick assign a subject to a teacher for multiple classes"""
    subject_name = request.form.get('subject_name', '').strip()
    class_ids = request.form.getlist('class_ids')  # Get multiple class IDs
    
    if not subject_name or not class_ids:
        flash('Please enter subject name and select at least one class.', 'warning')
        return redirect(url_for('admin_teachers'))
    
    # Get the subject's actual semester from the subjects table
    conn = db.get_db_connection()
    semester = None
    if conn:
        cur = conn.cursor()
        # Look up the subject's semester
        cur.execute("""
            SELECT semester FROM subjects
            WHERE LOWER(name) = LOWER(%s) AND semester IS NOT NULL
            LIMIT 1
        """, (subject_name,))
        subj_row = cur.fetchone()
        if subj_row:
            semester = subj_row[0]
        
        if semester:
            # VALIDATION: Ensure all selected classes belong to this semester
            cur.execute("""
                SELECT id FROM classes 
                WHERE id = ANY(%s) AND semester != %s
            """, (class_ids, semester))
            wrong_classes = cur.fetchall()
            if wrong_classes:
                cur.close()
                conn.close()
                flash(f'⚠️ ERROR: "{subject_name}" belongs to Semester {semester}. You can only assign it to Semester {semester} classes!', 'danger')
                return redirect(url_for('admin_teachers'))
        
        cur.close()
        conn.close()
    
    if not semester:
        # Subject doesn't exist yet — derive semester from selected classes
        conn2 = db.get_db_connection()
        if conn2:
            cur2 = conn2.cursor()
            cur2.execute("SELECT DISTINCT semester FROM classes WHERE id = ANY(%s)", (class_ids,))
            rows = cur2.fetchall()
            if len(rows) == 1:
                semester = rows[0][0]
            else:
                cur2.close()
                conn2.close()
                flash('⚠️ ERROR: Select classes from only ONE semester!', 'danger')
                return redirect(url_for('admin_teachers'))
            cur2.close()
            conn2.close()
    
    if not semester:
        flash('Error determining semester for classes.', 'danger')
        return redirect(url_for('admin_teachers'))
    
    success_count = 0
    for class_id in class_ids:
        # Create or get the subject for this semester
        subject_id = db.create_subject(subject_name, semester)
        if subject_id:
            # Always create a new assignment for this teacher+subject+class.
            # Multiple teachers can be assigned to the same subject+class independently.
            # assign_teacher_to_subject uses ON CONFLICT DO NOTHING so duplicates are safe.
            assignment_id = db.assign_teacher_to_subject(teacher_id, subject_id, class_id)
            if assignment_id:
                success_count += 1
            else:
                # assignment_id is None means it already existed (ON CONFLICT DO NOTHING)
                # Still count as success since the assignment is already there
                success_count += 1
    
    if success_count > 0:
        flash(f'Subject "{subject_name}" assigned to {success_count} class(es) in Semester {semester} successfully!', 'success')
    else:
        flash('Error assigning subject.', 'danger')
    
    return redirect(url_for('admin_teachers'))


@app.route('/admin/teachers/unassign-subject/<int:assignment_id>', methods=['POST'])
@admin_required
def admin_unassign_subject(assignment_id):
    """Remove a teacher assignment"""
    result = db.remove_teacher_assignment(assignment_id)
    
    if result:
        flash('Subject unassigned successfully.', 'success')
    else:
        flash('Error unassigning subject.', 'danger')
    
    return redirect(url_for('admin_teachers'))


@app.route('/admin/teachers/unassign-subject-ajax/<int:assignment_id>', methods=['POST'])
@admin_required
def admin_unassign_subject_ajax(assignment_id):
    """AJAX: Remove a teacher assignment without page reload"""
    result = db.remove_teacher_assignment(assignment_id)
    if result is not None:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Could not remove assignment'}), 400


@app.route('/admin/teachers/<int:teacher_id>/assign-subject-ajax', methods=['POST'])
@admin_required
def admin_assign_subject_ajax(teacher_id):
    """AJAX: Assign a subject to a teacher for multiple classes"""
    subject_name = request.form.get('subject_name', '').strip()
    class_ids = request.form.getlist('class_ids')

    if not subject_name or not class_ids:
        return jsonify({'success': False, 'error': 'Please select a subject and at least one class.'}), 400

    # Get subject semester
    conn = db.get_db_connection()
    semester = None
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT semester FROM subjects WHERE LOWER(name) = LOWER(%s) AND semester IS NOT NULL LIMIT 1", (subject_name,))
        row = cur.fetchone()
        if row:
            semester = row[0]
        cur.close()
        conn.close()

    if not semester:
        conn2 = db.get_db_connection()
        if conn2:
            cur2 = conn2.cursor()
            cur2.execute("SELECT DISTINCT semester FROM classes WHERE id = ANY(%s)", (class_ids,))
            rows = cur2.fetchall()
            semester = rows[0][0] if len(rows) == 1 else None
            cur2.close()
            conn2.close()

    if not semester:
        return jsonify({'success': False, 'error': 'Could not determine semester.'}), 400

    success_count = 0
    new_assignments = []
    for class_id in class_ids:
        subject_id = db.create_subject(subject_name, semester)
        if subject_id:
            assignment_id = db.assign_teacher_to_subject(teacher_id, subject_id, class_id)
            success_count += 1
            # Get class info for return
            conn3 = db.get_db_connection()
            if conn3:
                cur3 = conn3.cursor()
                cur3.execute("""
                    SELECT ta.id as assignment_id, s.name, c.year, c.section, c.shift, c.semester
                    FROM teacher_assignments ta
                    JOIN subjects s ON ta.subject_id = s.id
                    JOIN classes c ON ta.class_id = c.id
                    WHERE ta.teacher_id = %s AND ta.subject_id = %s AND ta.class_id = %s
                """, (teacher_id, subject_id, class_id))
                row = cur3.fetchone()
                if row:
                    new_assignments.append({
                        'assignment_id': row[0],
                        'name': row[1],
                        'year': row[2],
                        'section': row[3],
                        'shift': row[4],
                        'semester': row[5]
                    })
                cur3.close()
                conn3.close()

    if success_count > 0:
        return jsonify({'success': True, 'count': success_count, 'assignments': new_assignments})
    return jsonify({'success': False, 'error': 'Error assigning subject.'}), 400


# =============================================
# ADMIN - CLASS MANAGEMENT
# =============================================

@app.route('/admin/classes')
@admin_required
def admin_classes():
    """Manage classes - shows all 4 semesters"""
    classes = db.get_all_classes() or []
    class_counts, semester_totals = db.get_class_student_counts()
    return render_template('admin/classes.html', classes=classes, class_counts=class_counts, semester_totals=semester_totals)


@app.route('/admin/semester/<int:semester>/<shift>/<section>')
@admin_required
def admin_semester_students(semester, shift, section):
    """View students by Semester/Shift/Class"""
    students = db.get_students_by_semester(semester, shift, section) or []
    year = 1 if semester <= 2 else 2
    
    # Build class_info for the template
    class_info = {
        'year': year,
        'semester': semester,
        'shift': shift,
        'section': section
    }
    
    return render_template('admin/class_students.html', class_info=class_info, students=students)


@app.route('/admin/classes/add', methods=['GET', 'POST'])
@admin_required
def admin_add_class():
    """Add new class"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        year = request.form.get('year', type=int)
        semester = request.form.get('semester', type=int)
        section = request.form.get('section', '').strip()
        shift = request.form.get('shift', '').strip()
        
        # Validation
        if not all([name, year, semester, section, shift]):
            flash('Please fill in all required fields.', 'warning')
            return render_template('admin/add_class.html')
        
        # Validate year-semester combination
        if year == 1 and semester not in [1, 2]:
            flash('Year 1 can only have Semester 1 or 2.', 'danger')
            return render_template('admin/add_class.html')
        if year == 2 and semester not in [3, 4]:
            flash('Year 2 can only have Semester 3 or 4.', 'danger')
            return render_template('admin/add_class.html')
        
        class_id = db.create_class(name, year, semester, section, shift, description)
        
        if class_id:
            flash(f'Class "{name}" created successfully!', 'success')
            return redirect(url_for('admin_classes'))
        else:
            flash('Error creating class. This class combination may already exist.', 'danger')
    
    return render_template('admin/add_class.html')


@app.route('/admin/classes/<int:class_id>/students')
@admin_required
def admin_class_students(class_id):
    """View students in a class"""
    class_info = db.get_class_by_id(class_id)
    if not class_info:
        flash('Class not found.', 'danger')
        return redirect(url_for('admin_classes'))
    
    students = db.get_students_by_class(class_id) or []
    return render_template('admin/class_students.html', class_info=class_info, students=students)


# =============================================
# ADMIN - STUDENT MANAGEMENT
# =============================================

@app.route('/admin/students')
@admin_required
def admin_students():
    """Manage students with Year/Semester/Shift/Class filters"""
    year = request.args.get('year')
    semester = request.args.get('semester')
    shift = request.args.get('shift')
    section = request.args.get('section')
    
    # Get all students with new structure
    students = db.get_all_students_v2() or []
    
    # Apply filters
    if year:
        students = [s for s in students if s.get('year') == int(year)]
    if semester:
        students = [s for s in students if s.get('semester') == int(semester)]
    if shift:
        students = [s for s in students if s.get('shift') == shift]
    if section:
        if section == 'none':
            students = [s for s in students if not s.get('section')]
        else:
            students = [s for s in students if s.get('section') == section]
    
    return render_template('admin/students.html', students=students)


@app.route('/admin/students/assign-sections', methods=['GET', 'POST'])
@admin_required
def admin_assign_sections():
    """Assign classes to students who don't have one"""
    if request.method == 'POST':
        # Process class assignments
        for key, value in request.form.items():
            if key.startswith('section_') and value:
                student_id = int(key.replace('section_', ''))
                db.assign_student_section(student_id, value)
        flash('Classes assigned successfully!', 'success')
        return redirect(url_for('admin_students'))
    
    # Get students without sections, grouped by year and shift
    students = db.get_students_without_section() or []
    
    # Group students by year and shift
    grouped = {}
    for s in students:
        key = f"Year {s.get('year', '?')} - {(s.get('shift') or 'unknown').title()}"
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(s)
    
    return render_template('admin/assign_sections.html', grouped_students=grouped)


@app.route('/admin/students/add', methods=['GET', 'POST'])
@admin_required
def admin_add_student():
    """Add new student with Semester + Shift + Class (optional)"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip() or None  # Empty string becomes None
        semester = request.form.get('semester', type=int)
        shift = request.form.get('shift')
        section = request.form.get('section') or None  # Optional now
        phone = request.form.get('phone', '').strip() or None  # Empty string becomes None
        
        # Validation - removed username, student_number, and section from required
        if not all([password, full_name, semester, shift]):
            flash('Please fill in all required fields.', 'warning')
            return render_template('admin/add_student.html')
        
        # Derive year from semester
        year = 1 if semester <= 2 else 2
        
        # Auto-generate unique student number (MIS + year + 5-digit sequence)
        import datetime
        current_year = datetime.datetime.now().year
        
        # Get the highest student number to generate next one
        result = db.execute_query(
            "SELECT student_number FROM students WHERE student_number LIKE %s ORDER BY student_number DESC LIMIT 1",
            (f'MIS{current_year}%',),
            fetch_one=True
        )
        
        if result and result['student_number']:
            # Extract the sequence number and increment
            last_num = result['student_number']
            try:
                seq = int(last_num[-5:]) + 1
            except:
                seq = 1
        else:
            seq = 1
        
        student_number = f"MIS{current_year}{seq:05d}"
        
        # Auto-generate username from student number
        username = student_number.lower()
        
        # Check if username exists (shouldn't happen with unique student numbers)
        if db.get_user_by_username(username):
            flash('Error generating unique student ID. Please try again.', 'danger')
            return render_template('admin/add_student.html')
        
        # Create user
        password_hash = generate_password_hash(password)
        user_id = db.create_user(username, password_hash, full_name, 'student', email, password)
        
        if user_id:
            db.create_student_with_semester(user_id, year, semester, shift, section, student_number, phone)
            flash(f'Student "{full_name}" added with ID: {student_number}!', 'success')
            return redirect(url_for('admin_students'))
        else:
            flash('Error creating student.', 'danger')
    
    return render_template('admin/add_student.html')


@app.route('/admin/students/add-ajax', methods=['POST'])
@admin_required
def admin_add_student_ajax():
    """AJAX endpoint to add student without page reload"""
    from flask import jsonify
    
    try:
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip() or None
        semester = request.form.get('semester', type=int)
        shift = request.form.get('shift')
        section = request.form.get('section') or None
        phone = request.form.get('phone', '').strip() or None
        
        # Derive year from semester
        year = 1 if semester and semester <= 2 else 2
        
        # Validation
        if not all([password, full_name, semester, shift]):
            return jsonify({'success': False, 'message': 'Please fill in all required fields.'})
        
        # Auto-generate unique student number
        import datetime
        current_year = datetime.datetime.now().year
        
        result = db.execute_query(
            "SELECT student_number FROM students WHERE student_number LIKE %s ORDER BY student_number DESC LIMIT 1",
            (f'MIS{current_year}%',),
            fetch_one=True
        )
        
        if result and result.get('student_number'):
            try:
                seq = int(result['student_number'][-5:]) + 1
            except:
                seq = 1
        else:
            seq = 1
        
        student_number = f"MIS{current_year}{seq:05d}"
        username = student_number.lower()
        
        if db.get_user_by_username(username):
            return jsonify({'success': False, 'message': 'Error generating unique student ID. Please try again.'})
        
        # Create user
        password_hash = generate_password_hash(password)
        user_id = db.create_user(username, password_hash, full_name, 'student', email, password)
        
        if user_id:
            db.create_student_with_semester(user_id, year, semester, shift, section, student_number, phone)
            return jsonify({
                'success': True,
                'message': f'Student "{full_name}" added with ID: {student_number}',
                'student': {
                    'name': full_name,
                    'student_number': student_number,
                    'semester': semester,
                    'shift': shift,
                    'section': section
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Error creating student user account.'})
    except Exception as e:
        print(f"Error adding student: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'})


@app.route('/admin/students/<int:student_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_student(student_id):
    """Edit student with Year/Shift/Section"""
    student = db.get_student_by_id(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('admin_students'))
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        year = request.form.get('year')
        semester = request.form.get('semester')
        shift = request.form.get('shift')
        section = request.form.get('section') or None
        student_number = request.form.get('student_number', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        
        if not full_name or not year or not semester or not shift:
            flash('Please fill in all required fields (Full Name, Year, Semester, Shift).', 'warning')
            return render_template('admin/edit_student.html', student=student)
        
        # Update student with new fields including semester
        db.update_student_v2(student_id, full_name, email, int(year), int(semester), shift, section, student_number, phone)
        
        # Update password if provided
        if password:
            password_hash = generate_password_hash(password)
            db.execute_query("UPDATE users SET password_hash = %s WHERE id = %s", 
                           (password_hash, student['user_id']))
        
        flash('Student updated successfully!', 'success')
        return redirect(url_for('admin_students'))
    
    return render_template('admin/edit_student.html', student=student)


@app.route('/admin/students/<int:student_id>/edit-ajax', methods=['POST'])
@admin_required
def admin_edit_student_ajax(student_id):
    """Edit student via AJAX"""
    student = db.get_student_by_id(student_id)
    if not student:
        return jsonify({'success': False, 'message': 'Student not found.'})
    
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    year = request.form.get('year')
    semester = request.form.get('semester')
    shift = request.form.get('shift')
    section = request.form.get('section') or None
    student_number = request.form.get('student_number', '').strip()
    phone = request.form.get('phone', '').strip()
    password = request.form.get('password', '')
    
    if not full_name or not year or not semester or not shift:
        return jsonify({'success': False, 'message': 'Please fill in all required fields.'})
    
    # Update student
    db.update_student_v2(student_id, full_name, email, int(year), int(semester), shift, section, student_number, phone)
    
    # Update password if provided
    if password:
        password_hash = generate_password_hash(password)
        db.execute_query("UPDATE users SET password_hash = %s WHERE id = %s", 
                       (password_hash, student['user_id']))
    
    # Return updated student data
    return jsonify({
        'success': True,
        'message': 'Student updated successfully!',
        'student': {
            'id': student_id,
            'full_name': full_name,
            'email': email,
            'year': int(year),
            'semester': int(semester),
            'shift': shift,
            'section': section,
            'student_number': student_number,
            'phone': phone
        }
    })



@app.route('/admin/students/<int:student_id>/delete', methods=['POST'])
@admin_required
def admin_delete_student(student_id):
    """Delete student"""
    result = db.delete_student(student_id)
    if result:
        flash('Student deleted successfully.', 'success')
    else:
        flash('Error deleting student.', 'danger')
    return redirect(url_for('admin_students'))


# =============================================
# ADMIN - SUBJECT MANAGEMENT
# =============================================

@app.route('/admin/subjects')
@admin_required
def admin_subjects():
    """Manage subjects - show general definitions only"""
    subjects = db.get_subjects_grouped_by_semester() or []
    return render_template('admin/subjects.html', subjects=subjects)


@app.route('/admin/subjects/add', methods=['GET', 'POST'])
@admin_required
def admin_add_subject():
    """Add new subject for a specific semester"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        year = request.form.get('year', type=int)
        semester = request.form.get('semester', type=int)
        description = request.form.get('description', '').strip()
        credits = request.form.get('credits', type=int) or 6
        
        if not name or not semester:
            flash('Please enter subject name and select semester.', 'warning')
            return render_template('admin/add_subject.html')
        
        if credits < 1 or credits > 30:
            flash('Credits must be between 1 and 30.', 'warning')
            return render_template('admin/add_subject.html')
        
        # Create subject for this semester
        subject_id = db.create_subject(name, semester, description, credits)
        
        if subject_id:
            flash(f'Subject "{name}" created for Semester {semester} with {credits} credits!', 'success')
            return redirect(url_for('admin_subjects'))
        else:
            flash('Subject already exists or error creating subject.', 'info')
    
    return render_template('admin/add_subject.html')


@app.route('/admin/subjects/<int:subject_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_subject(subject_id):
    """Edit subject"""
    subject = db.get_subject_by_id(subject_id)
    if not subject:
        flash('Subject not found.', 'danger')
        return redirect(url_for('admin_subjects'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        year = request.form.get('year', type=int)
        semester = request.form.get('semester', type=int)
        description = request.form.get('description', '').strip()
        credits = request.form.get('credits', type=int) or 6
        
        if not name or not semester:
            flash('Please enter subject name and select semester.', 'warning')
            return render_template('admin/edit_subject.html', subject=subject)
        
        if credits < 1 or credits > 30:
            flash('Credits must be between 1 and 30.', 'warning')
            return render_template('admin/edit_subject.html', subject=subject)
        
        db.update_subject(subject_id, name, semester, description, credits)
        flash('Subject updated successfully!', 'success')
        return redirect(url_for('admin_subjects'))
    
    return render_template('admin/edit_subject.html', subject=subject)


@app.route('/admin/subjects/<int:subject_id>/delete', methods=['POST'])
@admin_required
def admin_delete_subject(subject_id):
    """Delete subject"""
    result = db.delete_subject(subject_id)
    if result:
        flash('Subject deleted successfully.', 'success')
    else:
        flash('Error deleting subject.', 'danger')
    return redirect(url_for('admin_subjects'))


@app.route('/admin/subjects/<int:subject_id>/toggle-results', methods=['POST'])
@admin_required
def admin_toggle_subject_results(subject_id):
    """Toggle results publishing for a subject (admin final control)"""
    try:
        data = request.get_json()
        published = data.get('published', False)
        
        result = db.toggle_subject_results_published(subject_id, published)
        
        if result:
            status = 'published' if published else 'unpublished'
            return jsonify({
                'success': True,
                'message': f'Results {status} successfully',
                'published': published
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to update results status'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
    
    return render_template('admin/add_subject.html', classes=classes, teachers=teachers)


@app.route('/admin/publish-semester-results/<int:semester>', methods=['POST'])
@admin_required
def admin_publish_semester_results(semester):
    """Publish all subject results for an entire semester"""
    try:
        if semester not in [1, 2, 3, 4]:
            return jsonify({
                'success': False,
                'message': 'Invalid semester'
            }), 400
        
        result = db.publish_semester_results(semester)
        
        if result:
            return jsonify({
                'success': True,
                'message': f'All results for Semester {semester} have been published successfully!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to publish semester results'
            }), 500
    except Exception as e:
        print(f"Error publishing semester results: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


# =============================================
# ADMIN - GRADE COMPONENTS (Grading Rubric)
# =============================================

@app.route('/admin/subjects/<int:subject_id>/grading')
@admin_required
def admin_subject_grading(subject_id):
    """Manage grade distribution/rubric for a subject"""
    subject = db.get_subject_by_id(subject_id)
    if not subject:
        flash('Subject not found!', 'danger')
        return redirect(url_for('admin_subjects'))
    
    # Get grade components for this subject
    components = db.get_grade_components_by_subject(subject_id) or []
    
    # DEBUG: Print component order
    print(f"\n=== Loading grading page for subject {subject_id} ===")
    print("Components in order retrieved:")
    for comp in components:
        print(f"  [{comp['display_order']}] {comp['component_type']}: {comp['component_name']}")
    print("=== End component list ===\n")
    
    # Calculate total weight
    total_weight = db.get_subject_total_weight(subject_id)
    
    # Get summary by type
    summary = db.get_grade_components_summary(subject_id) or []
    
    # Check if valid (total = 100%)
    is_valid = abs(total_weight - 100.0) < 0.01
    
    return render_template('admin/subject_grading.html',
                         subject=subject,
                         components=components,
                         total_weight=total_weight,
                         is_valid=is_valid,
                         summary=summary)


@app.route('/admin/subjects/<int:subject_id>/grading/add', methods=['POST'])
@admin_required
def admin_add_grade_component(subject_id):
    """Add grade component(s) to subject - supports multiple items of same type"""
    subject = db.get_subject_by_id(subject_id)
    if not subject:
        flash('Subject not found!', 'danger')
        return redirect(url_for('admin_subjects'))
    
    component_type = request.form.get('component_type')
    quantity = request.form.get('quantity', type=int, default=1)
    total_weight = request.form.get('weight_percentage', type=float)
    display_order = request.form.get('display_order', type=int, default=0)
    midterm_structure = request.form.get('midterm_structure', 'single')
    
    # Type display names
    type_names = {
        'homework': 'Homework',
        'quiz': 'Quiz',
        'report': 'Report',
        'project': 'Project',
        'exam': 'Exam',
        'midterm': 'Midterm',
        'final': 'Final',
        'lab_report': 'Lab Report',
        'activity': 'Activity',
        'seminar': 'Seminar'
    }
    
    # Handle split midterm specially
    if component_type == 'midterm' and midterm_structure == 'split':
        practical_weight = request.form.get('practical_weight', type=float)
        theoretical_weight = request.form.get('theoretical_weight', type=float)
        
        if not practical_weight or not theoretical_weight:
            flash('Both practical and theoretical weights are required for split midterm!', 'danger')
            return redirect(url_for('admin_subject_grading', subject_id=subject_id))
        
        total_midterm_weight = practical_weight + theoretical_weight
        
        # Check if adding this would exceed 100%
        current_total = db.get_subject_total_weight(subject_id)
        if current_total + total_midterm_weight > 100.01:
            flash(f'Cannot add! Total weight would be {current_total + total_midterm_weight:.2f}% (max 100%)', 'danger')
            return redirect(url_for('admin_subject_grading', subject_id=subject_id))
        
        # Max score equals weight for split midterm
        practical_max = practical_weight
        theoretical_max = theoretical_weight
        
        # Add Midterm Practical
        practical_id = db.add_grade_component(
            subject_id,
            'midterm',
            'Midterm Practical',
            practical_max,
            practical_weight,
            display_order
        )
        
        # Add Midterm Theoretical
        theoretical_id = db.add_grade_component(
            subject_id,
            'midterm',
            'Midterm Theoretical',
            theoretical_max,
            theoretical_weight,
            display_order + 1
        )
        
        if practical_id and theoretical_id:
            flash(f'Midterm split added! Practical: {practical_weight}% ({practical_max} pts), Theoretical: {theoretical_weight}% ({theoretical_max} pts)', 'success')
        else:
            flash('Error adding split midterm!', 'danger')
        
        return redirect(url_for('admin_subject_grading', subject_id=subject_id))
    
    # Validation for regular components
    if not all([component_type, total_weight is not None]):
        flash('All fields are required!', 'danger')
        return redirect(url_for('admin_subject_grading', subject_id=subject_id))
    
    if component_type != 'midterm' or midterm_structure == 'single':
        if quantity < 1 or quantity > 20:
            flash('Quantity must be between 1 and 20!', 'danger')
            return redirect(url_for('admin_subject_grading', subject_id=subject_id))
    
    if total_weight < 0 or total_weight > 100:
        flash('Weight percentage must be between 0 and 100!', 'danger')
        return redirect(url_for('admin_subject_grading', subject_id=subject_id))
    
    # Check if adding this would exceed 100%
    current_total = db.get_subject_total_weight(subject_id)
    if current_total + total_weight > 100.01:
        flash(f'Cannot add! Total weight would be {current_total + total_weight:.2f}% (max 100%)', 'danger')
        return redirect(url_for('admin_subject_grading', subject_id=subject_id))
    
    # Get existing count of this type for numbering
    existing_count = db.get_component_count_by_type(subject_id, component_type)
    
    # CRITICAL: All items use the SAME max_score = total_weight
    # This way teachers enter scores 0-[total_weight] for each item
    # Example: 3 homeworks, 5% total → each max_score = 5
    max_scores = [total_weight] * quantity
    
    # Calculate individual weight per item with HIGH PRECISION
    # Use Decimal for exact calculation to avoid rounding errors
    from decimal import Decimal, ROUND_HALF_UP
    
    total_decimal = Decimal(str(total_weight))
    quantity_decimal = Decimal(str(quantity))
    individual_weight = total_decimal / quantity_decimal
    
    # Distribute weights ensuring EXACT total
    weights = []
    running_total = Decimal('0')
    
    for i in range(quantity - 1):
        # Round to 2 decimal places
        weight = individual_weight.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        weights.append(float(weight))
        running_total += weight
    
    # Last item gets the remainder to ensure EXACT total
    last_weight = total_decimal - running_total
    weights.append(float(last_weight))
    
    # Verify total is EXACT (critical for legal compliance)
    actual_total = sum(weights)
    if abs(actual_total - total_weight) > 0.001:
        flash(f'ERROR: Weight calculation mismatch! Expected {total_weight}%, got {actual_total}%. Please report this bug!', 'danger')
        return redirect(url_for('admin_subject_grading', subject_id=subject_id))
    
    # Add components
    added_count = 0
    type_display = type_names.get(component_type, component_type.title())
    
    for i in range(quantity):
        component_number = existing_count + i + 1
        if quantity == 1:
            # Single item - just use type name
            component_name = type_display
        else:
            # Multiple items - numbered
            component_name = f"{type_display} {component_number}"
        
        component_id = db.add_grade_component(
            subject_id, 
            component_type, 
            component_name, 
            max_scores[i], 
            weights[i], 
            display_order + i
        )
        
        if component_id:
            added_count += 1
    
    if added_count == quantity:
        if quantity == 1:
            flash(f'Component "{type_display}" added! Weight: {total_weight}%, Max Score: {total_weight} pts', 'success')
        else:
            flash(f'{quantity} {type_display} components added! Total: {total_weight}%, Each max: {total_weight} pts. Average of scores → final {total_weight}%', 'success')
    else:
        flash(f'Error: Only {added_count} of {quantity} components were added!', 'warning')
    
    return redirect(url_for('admin_subject_grading', subject_id=subject_id))


@app.route('/admin/subjects/<int:subject_id>/grading/<int:component_id>/delete', methods=['POST'])
@admin_required
def admin_delete_grade_component(subject_id, component_id):
    """Delete a grade component"""
    result = db.delete_grade_component(component_id)
    if result:
        flash('Component deleted successfully!', 'success')
    else:
        flash('Error deleting component!', 'danger')
    
    return redirect(url_for('admin_subject_grading', subject_id=subject_id))


@app.route('/admin/subjects/<int:subject_id>/grading/<int:component_id>/edit', methods=['POST'])
@admin_required
def admin_edit_grade_component(subject_id, component_id):
    """Edit a grade component"""
    component_type = request.form.get('component_type')
    component_name = request.form.get('component_name', '').strip()
    max_score = request.form.get('max_score', type=float)
    weight_percentage = request.form.get('weight_percentage', type=float)
    display_order = request.form.get('display_order', type=int, default=0)
    
    # Validation
    if not all([component_type, component_name, max_score, weight_percentage is not None]):
        flash('All fields are required!', 'danger')
        return redirect(url_for('admin_subject_grading', subject_id=subject_id))
    
    # Update component
    result = db.update_grade_component(component_id, component_type, component_name, max_score, weight_percentage, display_order)
    
    if result:
        flash('Component updated successfully!', 'success')
    else:
        flash('Error updating component!', 'danger')
    
    return redirect(url_for('admin_subject_grading', subject_id=subject_id))


@app.route('/admin/subjects/<int:subject_id>/grading/delete-category/<component_type>', methods=['POST'])
@admin_required
def admin_delete_grade_category(subject_id, component_type):
    """Delete all components of a specific type"""
    print(f"=== DELETE CATEGORY: subject_id={subject_id}, component_type={component_type} ===")
    
    result = db.delete_grade_components_by_type(subject_id, component_type)
    print(f"Delete result: {result}")
    
    type_names = {
        'homework': 'Homework',
        'quiz': 'Quiz',
        'report': 'Report',
        'project': 'Project',
        'exam': 'Exam',
        'midterm': 'Midterm',
        'final': 'Final',
        'lab_report': 'Lab Report',
        'activity': 'Activity',
        'seminar': 'Seminar'
    }
    
    type_display = type_names.get(component_type, component_type.title())
    
    if result and len(result) > 0:
        flash(f'✓ All {type_display} components deleted successfully! ({len(result)} items removed)', 'success')
    else:
        flash(f'No {type_display} components found to delete!', 'warning')
    
    return redirect(url_for('admin_subject_grading', subject_id=subject_id))


@app.route('/admin/subjects/<int:subject_id>/grading/edit-category/<component_type>', methods=['POST'])
@admin_required
def admin_edit_grade_category(subject_id, component_type):
    """Edit total weight for all components of a specific type"""
    new_total_weight = request.form.get('new_total_weight', type=float)
    
    if not new_total_weight or new_total_weight < 0:
        flash('Invalid weight value!', 'danger')
        return redirect(url_for('admin_subject_grading', subject_id=subject_id))
    
    # Get current weight of this type
    components = db.get_grade_components_by_subject(subject_id)
    current_type_weight = float(sum(c['weight_percentage'] for c in components if c['component_type'] == component_type))
    other_weight = float(sum(c['weight_percentage'] for c in components if c['component_type'] != component_type))
    
    # Check if new total would exceed 100%
    if other_weight + new_total_weight > 100.01:
        flash(f'Cannot update! Total would be {other_weight + new_total_weight:.2f}% (max 100%)', 'danger')
        return redirect(url_for('admin_subject_grading', subject_id=subject_id))
    
    result = db.update_grade_components_by_type(subject_id, component_type, new_total_weight)
    
    type_names = {
        'homework': 'Homework',
        'quiz': 'Quiz',
        'report': 'Report',
        'project': 'Project',
        'exam': 'Exam',
        'midterm': 'Midterm',
        'final': 'Final',
        'lab_report': 'Lab Report',
        'activity': 'Activity',
        'seminar': 'Seminar'
    }
    
    type_display = type_names.get(component_type, component_type.title())
    
    if result:
        flash(f'{type_display} category updated! New total: {new_total_weight}%', 'success')
    else:
        flash(f'Error updating {type_display} category!', 'danger')
    
    return redirect(url_for('admin_subject_grading', subject_id=subject_id))


@app.route('/admin/subjects/<int:subject_id>/grading/reorder', methods=['POST'])
@admin_required
def admin_reorder_grade_components(subject_id):
    """Update display order for component categories based on new ordering"""
    category_order = request.form.get('category_order')
    
    if not category_order:
        flash('No order data received!', 'danger')
        return redirect(url_for('admin_subject_grading', subject_id=subject_id))
    
    # Parse category order: "homework,quiz,exam,final"
    categories = [c.strip() for c in category_order.split(',') if c.strip()]
    
    if not categories:
        flash('Invalid order data!', 'danger')
        return redirect(url_for('admin_subject_grading', subject_id=subject_id))
    
    # Debug output
    print(f"Reordering categories for subject {subject_id}: {categories}")
    
    # Update display order for all components based on category position
    result = db.reorder_categories_by_type(subject_id, categories)
    
    if result:
        flash(f'Successfully reordered {len(categories)} categories!', 'success')
    else:
        flash('Failed to update category order!', 'danger')
    
    return redirect(url_for('admin_subject_grading', subject_id=subject_id))


# =============================================
# ADMIN - ENROLLMENT PERIODS
# =============================================

@app.route('/admin/enrollment-periods')
@admin_required
def admin_enrollment_periods():
    """Manage enrollment periods"""
    from datetime import datetime
    periods = db.get_all_enrollment_periods()
    
    # Add status flags to each period
    now = datetime.now()
    for period in periods:
        period['is_active'] = period['start_date'] <= now <= period['end_date']
        period['is_upcoming'] = period['start_date'] > now
    
    return render_template('admin/enrollment_periods.html', periods=periods)


@app.route('/admin/enrollment-periods/add', methods=['POST'])
@admin_required
def admin_add_enrollment_period():
    """Create a new enrollment period"""
    from datetime import datetime
    
    semester = request.form.get('semester', type=int)
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    description = request.form.get('description', '')
    
    if not all([semester, start_date, end_date]):
        return jsonify({'success': False, 'error': 'All fields are required'}), 400
    
    try:
        # Convert to datetime
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        
        if end_dt <= start_dt:
            return jsonify({'success': False, 'error': 'End date must be after start date'}), 400
        
        # Create enrollment period
        result = db.create_enrollment_period(
            semester, 
            start_dt, 
            end_dt, 
            description, 
            session['user_id']
        )
        
        if result:
            return jsonify({'success': True, 'message': 'Enrollment period created successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to create enrollment period'}), 500
            
    except Exception as e:
        print(f"Error creating enrollment period: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/enrollment-periods/<int:period_id>/delete', methods=['POST'])
@admin_required
def admin_delete_enrollment_period(period_id):
    """Delete an enrollment period"""
    try:
        db.delete_enrollment_period(period_id)
        return jsonify({'success': True, 'message': 'Enrollment period deleted successfully'})
    except Exception as e:
        print(f"Error deleting enrollment period: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================
# TEACHER - ATTENDANCE
# =============================================

@app.route('/teacher/attendance')
@teacher_required
def teacher_attendance():
    """Attendance management page - grouped by subject name"""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    
    # Group subjects by name - ONE card per subject, with classes inside
    grouped_subjects = {}
    for s in subjects:
        name = s['name']
        if name not in grouped_subjects:
            grouped_subjects[name] = {'classes': []}
        
        # Parse class info from class_name (e.g., "Year 1 - Sem 1 - Section A - Morning")
        class_name = s.get('class_name', '')
        parts = class_name.split(' - ')
        year = parts[0].replace('Year ', '') if len(parts) > 0 else '?'
        semester = parts[1].replace('Sem ', '') if len(parts) > 1 else '?'
        section = parts[2].replace('Section ', '') if len(parts) > 2 else ''
        shift = parts[3].lower() if len(parts) > 3 else 'morning'
        
        grouped_subjects[name]['classes'].append({
            'subject_id': s['id'],
            'class_id': s.get('class_id'),
            'class_name': class_name,
            'year': year,
            'semester': semester,
            'section': section,
            'shift': shift
        })
    
    return render_template('teacher/attendance.html', grouped_subjects=grouped_subjects, teacher=teacher)


@app.route('/teacher/attendance/take/<int:subject_id>/<int:class_id>', methods=['GET', 'POST'])
@teacher_required
def teacher_take_attendance(subject_id, class_id):
    """Take attendance for a subject"""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get subject and class info - match both subject_id AND class_id
    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    subject = next((s for s in subjects if s['id'] == subject_id and s.get('class_id') == class_id), None)
    
    if not subject:
        flash('Subject not found or access denied.', 'danger')
        return redirect(url_for('teacher_attendance'))
    
    # Get only enrolled students from this specific class
    students = db.get_enrolled_students_for_subject(subject_id, class_id) or []
    attendance_date = request.args.get('date', date.today().isoformat())
    
    if request.method == 'POST':
        attendance_date = request.form.get('date', date.today().isoformat())
        
        for student in students:
            status = request.form.get(f'status_{student["id"]}', 'absent')
            notes = request.form.get(f'notes_{student["id"]}', '')
            db.record_attendance(student['id'], subject_id, teacher['id'], attendance_date, status, notes)
        
        flash('Attendance recorded successfully!', 'success')
        # Stay on the same page instead of redirecting
        return redirect(url_for('teacher_take_attendance', subject_id=subject_id, class_id=class_id, date=attendance_date))
    
    # Get existing attendance for the date
    existing_attendance = db.get_attendance_by_subject_date(subject_id, attendance_date) or []
    attendance_dict = {a['student_id']: a for a in existing_attendance}
    
    return render_template('teacher/take_attendance.html',
                         subject=subject,
                         students=students,
                         attendance_date=attendance_date,
                         attendance_dict=attendance_dict)


@app.route('/teacher/attendance/logs/<int:subject_id>/<int:class_id>')
@teacher_required
def teacher_attendance_logs(subject_id, class_id):
    """View attendance logs with filtering"""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    subject = next((s for s in subjects if s['id'] == subject_id and s.get('class_id') == class_id), None)
    
    if not subject:
        flash('Subject not found or access denied.', 'danger')
        return redirect(url_for('teacher_attendance'))
    
    # Get filter parameters
    student_id = request.args.get('student_id', type=int)
    status = request.args.get('status', '')
    
    # Get enrolled students from this specific class for filter dropdown
    students = db.get_enrolled_students_for_subject(subject_id, class_id) or []
    
    # Get all logs (no filter for grouping by date)
    all_logs = db.get_attendance_logs(subject_id) or []
    
    # Group logs by date
    logs_by_date = {}
    for log in all_logs:
        date_str = log['date'].strftime('%A, %B %d, %Y') if log['date'] else 'Unknown'
        if date_str not in logs_by_date:
            logs_by_date[date_str] = []
        logs_by_date[date_str].append(log)
    
    # Get student-specific logs if filtered
    student_logs = []
    if student_id:
        student_logs = db.get_attendance_logs(
            subject_id,
            student_id=student_id,
            status=status if status else None
        ) or []
    
    # Get summary
    summary = db.get_attendance_summary(subject_id) or []
    
    # Get all dates for reference
    dates = db.get_attendance_dates(subject_id) or []
    
    return render_template('teacher/attendance_logs.html',
                         subject=subject,
                         students=students,
                         logs_by_date=logs_by_date,
                         student_logs=student_logs,
                         summary=summary,
                         dates=dates,
                         filters={
                             'student_id': student_id,
                             'status': status
                         })


# =============================================
# TEACHER - GRADES
# =============================================

@app.route('/teacher/grades')
@teacher_required
def teacher_grades():
    """Grades management page - grouped by subject name"""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    
    # Group subjects by name
    grouped_subjects = {}
    for s in subjects:
        name = s['name']
        if name not in grouped_subjects:
            grouped_subjects[name] = {'classes': []}
        
        class_name = s.get('class_name', '')
        parts = class_name.split(' - ')
        year = parts[0].replace('Year ', '') if len(parts) > 0 else '?'
        semester = parts[1].replace('Sem ', '') if len(parts) > 1 else '?'
        section = parts[2].replace('Section ', '') if len(parts) > 2 else ''
        shift = parts[3].lower() if len(parts) > 3 else 'morning'
        
        grouped_subjects[name]['classes'].append({
            'subject_id': s['id'],
            'class_id': s.get('class_id'),
            'class_name': class_name,
            'year': year,
            'semester': semester,
            'section': section,
            'shift': shift
        })
    
    return render_template('teacher/grades.html', grouped_subjects=grouped_subjects, teacher=teacher)


@app.route('/teacher/grades/add/<int:subject_id>/<int:class_id>', methods=['GET', 'POST'])
@teacher_required
def teacher_add_grades(subject_id, class_id):
    """Add grades for a subject"""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    subject = next((s for s in subjects if s['id'] == subject_id and s.get('class_id') == class_id), None)
    
    if not subject:
        flash('Subject not found or access denied.', 'danger')
        return redirect(url_for('teacher_grades'))
    
    # Get only enrolled students from this specific class
    students = db.get_enrolled_students_for_subject(subject_id, class_id) or []
    
    # Get grade components (templates) created by admin
    components = db.get_grade_components_by_subject(subject_id) or []
    
    if request.method == 'POST':
        try:
            print("=== GRADE SUBMISSION DEBUG ===")
            print(f"Form data: {dict(request.form)}")
            
            student_id = request.form.get('student_id', '')
            grade_date_str = request.form.get('date', '').strip()
            
            # Use today's date if empty or invalid
            if not grade_date_str:
                grade_date = date.today().isoformat()
            else:
                grade_date = grade_date_str
            
            print(f"Student ID: {student_id}, Date: {grade_date}")
            print(f"\n=== PROCESSING GRADES FOR STUDENT {student_id} ===")
            
            if not student_id:
                return jsonify({'success': False, 'message': 'Student ID is required'}), 400
            
            # Process all component scores for this student
            grades_saved = 0
            errors = []
            saved_details = []
            
            for key in request.form.keys():
                if key.startswith('component_'):
                    component_id = int(key.replace('component_', ''))
                    score_str = request.form.get(key, '').strip()
                    
                    print(f"\n[{key}] Processing component_id={component_id}, score='{score_str}'")
                    
                    # Only save if score is provided (not empty string)
                    # This allows "0" as a valid score but ignores blank fields
                    if score_str != '':
                        try:
                            score = float(score_str)
                            
                            # Get component details
                            component = next((c for c in components if c['id'] == component_id), None)
                            if component:
                                print(f"[{key}] Component found: {component['component_name']}")
                                print(f"[{key}] Calling upsert_grade...")
                                
                                # Use upsert to update existing or insert new (saved as draft by default)
                                result = db.upsert_grade(
                                    int(student_id), 
                                    subject_id, 
                                    teacher['id'], 
                                    component['component_type'],
                                    component['component_name'],
                                    score, 
                                    float(component['max_score']), 
                                    grade_date,
                                    component_id,
                                    None,  # notes
                                    False  # published (draft mode)
                                )
                                
                                if result:
                                    print(f"[{key}] ✓ SUCCESS! Grade ID: {result}")
                                    grades_saved += 1
                                    saved_details.append(f"{component['component_name']}={score}")
                                else:
                                    error_msg = f"Failed to save {component['component_name']}"
                                    print(f"[{key}] ✗ FAILED! Result was None")
                                    errors.append(error_msg)
                            else:
                                error_msg = f"Component {component_id} not found"
                                errors.append(error_msg)
                                print(f"[{key}] ✗ ERROR: {error_msg}")
                        except ValueError as e:
                            error_msg = f"Invalid score value for component {component_id}: {e}"
                            errors.append(error_msg)
                            print(f"[{key}] ✗ VALUE ERROR: {e}")
                        except Exception as e:
                            error_msg = f"Exception for component {component_id}: {e}"
                            errors.append(error_msg)
                            print(f"[{key}] ✗ EXCEPTION: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"[{key}] Skipped (empty)")
            
            print(f"\n=== SUMMARY ===")
            print(f"Total grades saved: {grades_saved}")
            print(f"Saved: {saved_details}")
            print(f"Errors: {errors}")
            print(f"==================\n")
            
            if grades_saved > 0:
                message = f'{grades_saved} grade(s) saved successfully'
                if errors:
                    message += f'. Errors: {"; ".join(errors)}'
                return jsonify({'success': True, 'message': message}), 200
            else:
                error_msg = 'No valid grades were entered'
                if errors:
                    error_msg += f': {"; ".join(errors)}'
                return jsonify({'success': False, 'message': error_msg}), 400
                
        except Exception as e:
            print(f"ERROR SAVING GRADES: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    return render_template('teacher/add_grades.html', 
                          subject=subject, 
                          students=students, 
                          components=components,
                          today=date.today().isoformat())


@app.route('/teacher/grades/publish/<int:subject_id>/<int:class_id>', methods=['POST'])
@teacher_required
def teacher_publish_grades(subject_id, class_id):
    """Publish all draft grades for a subject/class"""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        return jsonify({'success': False, 'message': 'Teacher profile not found'}), 403
    
    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    subject = next((s for s in subjects if s['id'] == subject_id and s.get('class_id') == class_id), None)
    
    if not subject:
        return jsonify({'success': False, 'message': 'Subject not found or access denied'}), 403
    
    try:
        # Publish all draft grades for this subject/class
        db.publish_grades_for_subject(subject_id, class_id)
        return jsonify({'success': True, 'message': 'Grades published successfully! Students can now see their grades.'})
    except Exception as e:
        print(f"Error publishing grades: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/teacher/grades/student/<int:student_id>/subject/<int:subject_id>')
@teacher_required
def teacher_get_student_grades(student_id, subject_id):
    """Get existing grades for a specific student and subject (for pre-filling the modal)"""
    try:
        print(f"\n=== FETCHING GRADES: student_id={student_id}, subject_id={subject_id} ===")
        
        # Get grades for this student and subject
        query = """
            SELECT g.*, gc.component_name, gc.component_type, gc.max_score as component_max_score, gc.weight_percentage
            FROM grades g
            LEFT JOIN grade_components gc ON g.component_id = gc.id
            WHERE g.student_id = %s AND g.subject_id = %s
            ORDER BY g.date DESC, g.id DESC
        """
        grades = db.execute_query(query, (student_id, subject_id), fetch_all=True) or []
        
        print(f"Raw query returned {len(grades)} grade records")
        for g in grades:
            print(f"  - Grade ID {g.get('id')}: component_id={g.get('component_id')}, score={g.get('score')}, component_name={g.get('component_name')}")
        
        # Group by component_id to get the most recent grade for each component
        latest_grades = {}
        for grade in grades:
            comp_id = grade.get('component_id')
            if comp_id:
                if comp_id not in latest_grades:
                    latest_grades[comp_id] = {
                        'component_id': comp_id,
                        'score': grade['score'],
                        'max_score': grade['max_score'],
                        'weight_percentage': grade.get('weight_percentage', 0),
                        'component_name': grade.get('component_name', ''),
                        'date': grade['date'].isoformat() if hasattr(grade['date'], 'isoformat') else str(grade['date'])
                    }
                    print(f"  \u2713 Added component_id {comp_id}: score={grade['score']}")
                else:
                    print(f"  \u2717 Skipped duplicate component_id {comp_id}")
            else:
                print(f"  \u2717 Skipped grade with no component_id")
        
        result = {
            'success': True,
            'grades': list(latest_grades.values()),
            'debug': {
                'total_records': len(grades),
                'unique_components': len(latest_grades)
            }
        }
        
        print(f"Returning {len(latest_grades)} unique grades")
        print(f"Response: {result}")
        print("=== END FETCH ===\n")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error fetching student grades: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/teacher/grades/view/<int:subject_id>/<int:class_id>')
@teacher_required
def teacher_view_grades(subject_id, class_id):
    """View grades for a subject"""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    subject = next((s for s in subjects if s['id'] == subject_id and s.get('class_id') == class_id), None)
    
    if not subject:
        flash('Subject not found or access denied.', 'danger')
        return redirect(url_for('teacher_grades'))
    
    grades = db.get_grades_by_subject(subject_id) or []
    return render_template('teacher/view_grades.html', subject=subject, grades=grades)


# =============================================
# TEACHER - HOMEWORK
# =============================================

@app.route('/teacher/homework')
@teacher_required
def teacher_homework():
    """Homework management page"""
    from datetime import date
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    homework = db.get_homework_by_teacher(teacher['id']) or []
    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    today = date.today().isoformat()
    
    # Group homework rows by (title, subject_name, due_date) so same HW sent
    # to multiple classes appears as one row with expandable class list.
    grouped = {}
    for hw in homework:
        due_iso = hw['due_date'].isoformat() if hasattr(hw['due_date'], 'isoformat') else str(hw['due_date'])
        key = (hw['title'], hw['subject_name'], due_iso)
        if key not in grouped:
            grouped[key] = {
                'ids': [],
                'title': hw['title'],
                'description': hw.get('description', ''),
                'filename': hw.get('filename'),
                'file_size': hw.get('file_size'),
                'first_id': hw['id'],   # used for file download
                'subject_name': hw['subject_name'],
                'due_date': hw['due_date'],
                'due_iso': due_iso,
                'classes': [],
            }
        grouped[key]['ids'].append(hw['id'])
        grouped[key]['classes'].append(hw['class_name'])
    
    grouped_homework = list(grouped.values())
    return render_template('teacher/homework.html', grouped_homework=grouped_homework,
                           homework=homework, subjects=subjects, today=today)


@app.route('/teacher/homework/add', methods=['GET', 'POST'])
@teacher_required
def teacher_add_homework():
    """Add new homework"""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    
    # Get unique subject names for dropdown
    unique_subjects = sorted(set(s['name'] for s in subjects))
    
    if request.method == 'POST':
        assignment_ids = request.form.getlist('assignment_ids')  # Get list of selected assignment IDs
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date = request.form.get('due_date', '')
        
        if not all([assignment_ids, title, due_date]):
            flash('Please fill in all required fields.', 'warning')
            return render_template('teacher/add_homework.html', subjects=subjects, unique_subjects=unique_subjects)
        
        # Handle file upload (optional)
        filename = None
        file_path = None
        file_type = None
        file_size = None
        file_content = None
        
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '' and allowed_file(file.filename):
                # Create unique filename
                original_filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{original_filename}"
                
                # Read file content once
                file_content = file.read()
                file_size = len(file_content)
                file_type = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'unknown'
        
        # Create homework for each selected assignment (subject/class combination)
        success_count = 0
        for assignment_id in assignment_ids:
            assignment = next((s for s in subjects if s['assignment_id'] == int(assignment_id)), None)
            if assignment:
                # If file uploaded, save it to homework folder for this subject
                current_file_path = None
                if file_content:
                    homework_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'homework', f"subject_{assignment['id']}")
                    os.makedirs(homework_folder, exist_ok=True)
                    current_file_path = os.path.join(homework_folder, filename)
                    with open(current_file_path, 'wb') as f:
                        f.write(file_content)
                    # Store relative path
                    current_file_path = os.path.relpath(current_file_path, app.config['UPLOAD_FOLDER'])
                
                hw_id = db.create_homework(
                    assignment['class_id'], 
                    assignment['id'], 
                    teacher['id'], 
                    title, 
                    description, 
                    due_date,
                    filename=filename,
                    file_path=current_file_path,
                    file_type=file_type,
                    file_size=file_size
                )
                if hw_id:
                    success_count += 1
        
        if success_count > 0:
            flash(f'Homework created successfully for {success_count} class(es)!', 'success')
            return redirect(url_for('teacher_homework'))
        else:
            flash('Error creating homework.', 'danger')
    
    return render_template('teacher/add_homework.html', subjects=subjects, unique_subjects=unique_subjects)


@app.route('/teacher/homework/delete/<int:homework_id>', methods=['POST'])
@teacher_required
def teacher_delete_homework(homework_id):
    """Mark homework as done (delete it)"""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Delete homework - the database will verify teacher_id matches
    result = db.delete_homework(homework_id, teacher['id'])
    
    if result:
        flash('Homework marked as done and removed successfully!', 'success')
    else:
        flash('Error: Could not delete homework. You can only delete your own homework.', 'danger')
    
    return redirect(url_for('teacher_homework'))


@app.route('/teacher/homework/delete-group', methods=['POST'])
@teacher_required
def teacher_delete_homework_group():
    """Delete a group of homework rows (same HW sent to multiple classes) at once"""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    ids_raw = request.form.get('homework_ids', '')
    deleted = 0
    for id_str in ids_raw.split(','):
        try:
            hw_id = int(id_str.strip())
            if db.delete_homework(hw_id, teacher['id']):
                deleted += 1
        except (ValueError, TypeError):
            continue
    
    if deleted:
        flash(f'Homework marked as done and removed ({deleted} class(es)).', 'success')
    else:
        flash('Could not delete homework.', 'danger')
    
    return redirect(url_for('teacher_homework'))


@app.route('/homework/download/<int:homework_id>')
@login_required
def download_homework_file(homework_id):
    """Download homework attachment file"""
    # Get homework info
    query = "SELECT * FROM homework WHERE id = %s"
    homework = db.execute_query(query, (homework_id,), fetch_one=True)
    
    if not homework or not homework.get('filename'):
        flash('File not found.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))
    
    # Check access - teachers can download their own, students can download their class homework
    user_role = session.get('role')
    
    if user_role == 'teacher':
        teacher = db.get_teacher_by_user_id(session['user_id'])
        if teacher and homework['teacher_id'] != teacher['id']:
            flash('Access denied.', 'danger')
            return redirect(url_for('teacher_homework'))
    elif user_role == 'student':
        student = db.get_student_by_user_id(session['user_id'])
        if student and homework['class_id'] != student['class_id']:
            flash('Access denied. This homework is not for your class.', 'danger')
            return redirect(url_for('student_homework'))
    
    # Build full file path
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], homework['file_path'])
    
    if os.path.exists(file_path):
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        return send_from_directory(directory, filename, as_attachment=True, download_name=homework['filename'])
    else:
        flash('File not found on server.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))


# =============================================
# TEACHER - SCHEDULE (View Only)
# =============================================

@app.route('/teacher/schedule')
@teacher_required
def teacher_schedule():
    """View class schedules (read-only)"""
    return render_template('teacher/schedule.html')


@app.route('/teacher/api/schedule/<int:semester>/<shift>/<section>', methods=['GET'])
@teacher_required
def teacher_api_get_schedule(semester, shift, section):
    """API: Get schedule for a semester/shift/section (teacher read-only)"""
    import json
    schedule = db.get_schedule(semester, shift, section)
    if schedule and schedule.get('schedule_data'):
        data = schedule['schedule_data']
        if isinstance(data, (list, dict)):
            return {'success': True, 'data': data}
        return {'success': True, 'data': json.loads(data)}
    return {'success': True, 'data': []}


# =============================================
# TEACHER - WEEKLY TOPICS
# =============================================

@app.route('/teacher/topics')
@teacher_required
def teacher_topics():
    """Weekly topics management - grouped by subject name"""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    
    # Group subjects by name
    grouped_subjects = {}
    for s in subjects:
        name = s['name']
        if name not in grouped_subjects:
            grouped_subjects[name] = {'classes': []}
        
        class_name = s.get('class_name', '')
        parts = class_name.split(' - ')
        year = parts[0].replace('Year ', '') if len(parts) > 0 else '?'
        semester = parts[1].replace('Sem ', '') if len(parts) > 1 else '?'
        section = parts[2].replace('Section ', '') if len(parts) > 2 else ''
        shift = parts[3].lower() if len(parts) > 3 else 'morning'
        
        grouped_subjects[name]['classes'].append({
            'subject_id': s['id'],
            'class_name': class_name,
            'year': year,
            'semester': semester,
            'section': section,
            'shift': shift
        })
    
    return render_template('teacher/topics.html', grouped_subjects=grouped_subjects)


@app.route('/teacher/topics/<int:subject_id>', methods=['GET', 'POST'])
@teacher_required
def teacher_manage_topics(subject_id):
    """Manage exam/quiz notes for a subject"""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    subject = next((s for s in subjects if s['id'] == subject_id), None)
    
    if not subject:
        flash('Subject not found or access denied.', 'danger')
        return redirect(url_for('teacher_topics'))
    
    # Handle delete
    if request.method == 'POST' and request.form.get('action') == 'delete':
        note_id = request.form.get('note_id', type=int)
        if note_id:
            db.delete_exam_note(note_id, teacher['id'])
            flash('Note deleted.', 'success')
        return redirect(url_for('teacher_manage_topics', subject_id=subject_id))
    
    if request.method == 'POST':
        note_type = request.form.get('note_type', 'exam').strip()
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        exam_date = request.form.get('exam_date', '')
        
        if not title:
            flash('Please enter a title.', 'warning')
        else:
            db.create_exam_note(
                subject['class_id'], subject_id, teacher['id'],
                note_type, title,
                description if description else None,
                exam_date if exam_date else None
            )
            flash('Note saved successfully!', 'success')
        return redirect(url_for('teacher_manage_topics', subject_id=subject_id))
    
    notes = db.get_weekly_topics_by_subject(subject_id) or []
    return render_template('teacher/manage_topics.html', subject=subject, topics=notes)


# =============================================
# TEACHER - LECTURE FILES MANAGEMENT
# =============================================

@app.route('/teacher/files')
@teacher_required
def teacher_files():
    """View all uploaded lecture files"""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    files = db.get_lecture_files_by_teacher(teacher['id']) or []
    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    
    # Group file rows by (title, subject_name, week_number, file_name) so a file
    # uploaded to multiple classes shows as one row with an expandable class list.
    grouped = {}
    for f in files:
        key = (f['title'], f['subject_name'], f.get('week_number'), f.get('file_name'))
        if key not in grouped:
            grouped[key] = {
                'ids': [],
                'first_id': f['id'],
                'title': f['title'],
                'subject_name': f['subject_name'],
                'file_name': f.get('file_name'),
                'file_type': f.get('file_type'),
                'file_size': f.get('file_size'),
                'week_number': f.get('week_number'),
                'file_path': f.get('file_path'),
                'uploaded_at': f.get('uploaded_at'),
                'classes': [],
            }
        grouped[key]['ids'].append(f['id'])
        grouped[key]['classes'].append(f.get('class_name', ''))
    
    grouped_files = list(grouped.values())
    return render_template('teacher/files.html', grouped_files=grouped_files, files=files, subjects=subjects)


@app.route('/teacher/files/upload', methods=['GET', 'POST'])
@teacher_required
def teacher_upload_file():
    """Upload a new lecture file"""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    subjects = db.get_subjects_by_teacher(teacher['id']) or []
    
    # Get unique subject names for dropdown
    unique_subjects = sorted(set(s['name'] for s in subjects))
    
    if request.method == 'POST':
        assignment_ids = request.form.getlist('assignment_ids')  # Get list of selected assignment IDs
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        week_number = request.form.get('week_number', '')
        
        if 'file' not in request.files:
            flash('No file selected.', 'warning')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected.', 'warning')
            return redirect(request.url)
        
        if not assignment_ids or not title:
            flash('Please fill in all required fields.', 'warning')
            return render_template('teacher/upload_file.html', subjects=subjects, unique_subjects=unique_subjects)
        
        if file and allowed_file(file.filename):
            # Create unique filename
            original_filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{original_filename}"
            
            # Read file content once to avoid permission issues
            file_content = file.read()
            file_size = len(file_content)
            file_type = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'unknown'
            week_num = int(week_number) if week_number else None
            
            # Upload to each selected subject/class
            success_count = 0
            for assignment_id in assignment_ids:
                # Find the assignment (subject/class combination)
                assignment = next((s for s in subjects if s['assignment_id'] == int(assignment_id)), None)
                if not assignment:
                    continue
                    
                subject_id = assignment['id']
                class_id = assignment['class_id']
                
                # Create subject subfolder
                subject_folder = os.path.join(app.config['UPLOAD_FOLDER'], f"subject_{subject_id}")
                os.makedirs(subject_folder, exist_ok=True)
                
                file_path_individual = os.path.join(subject_folder, filename)
                
                # Write file content to each location
                with open(file_path_individual, 'wb') as f:
                    f.write(file_content)
                
                # Save to database with class_id
                db.create_lecture_file(
                    subject_id=subject_id,
                    teacher_id=teacher['id'],
                    class_id=class_id,
                    title=title,
                    description=description,
                    file_name=original_filename,
                    file_path=file_path_individual,
                    file_size=file_size,
                    file_type=file_type,
                    week_number=week_num
                )
                success_count += 1
            
            flash(f'File "{original_filename}" uploaded successfully to {success_count} class(es)!', 'success')
            return redirect(url_for('teacher_upload_file'))
        else:
            flash('File type not allowed. Allowed: PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX, TXT, ZIP, RAR, Images', 'danger')
    
    return render_template('teacher/upload_file.html', subjects=subjects, unique_subjects=unique_subjects)


@app.route('/teacher/files/delete/<int:file_id>', methods=['POST'])
@teacher_required
def teacher_delete_file(file_id):
    """Delete a lecture file"""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    file_info = db.get_lecture_file_by_id(file_id)
    if file_info and file_info['teacher_id'] == teacher['id']:
        # Delete physical file
        if os.path.exists(file_info['file_path']):
            os.remove(file_info['file_path'])
        # Delete from database
        db.delete_lecture_file(file_id)
        flash('File deleted successfully!', 'success')
    else:
        flash('File not found or access denied.', 'danger')
    
    return redirect(url_for('teacher_files'))


@app.route('/teacher/files/delete-group', methods=['POST'])
@teacher_required
def teacher_delete_file_group():
    """Delete all class copies of a grouped lecture file at once"""
    teacher = db.get_teacher_by_user_id(session['user_id'])
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    ids_raw = request.form.get('file_ids', '')
    physical_deleted = False
    deleted = 0
    for id_str in ids_raw.split(','):
        try:
            fid = int(id_str.strip())
            file_info = db.get_lecture_file_by_id(fid)
            if file_info and file_info['teacher_id'] == teacher['id']:
                # Delete physical file only once (all rows share same path)
                if not physical_deleted and file_info.get('file_path') and os.path.exists(file_info['file_path']):
                    os.remove(file_info['file_path'])
                    physical_deleted = True
                db.delete_lecture_file(fid)
                deleted += 1
        except (ValueError, TypeError):
            continue
    
    if deleted:
        flash(f'File deleted from {deleted} class(es) successfully!', 'success')
    else:
        flash('Could not delete file.', 'danger')
    
    return redirect(url_for('teacher_files'))


# =============================================
# FILE DOWNLOAD (For both teachers and students)
# =============================================

@app.route('/files/download/<int:file_id>')
@login_required
def download_file(file_id):
    """Download a lecture file"""
    file_info = db.get_lecture_file_by_id(file_id)
    
    if not file_info:
        flash('File not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check access rights
    user_role = session.get('role')
    
    if user_role == 'student':
        student = db.get_student_by_user_id(session['user_id'])
        if student:
            # Check if student's class_id matches the file's class_id
            if student['class_id'] != file_info['class_id']:
                flash('Access denied. This file is not for your class.', 'danger')
                return redirect(url_for('student_files'))
    
    if os.path.exists(file_info['file_path']):
        directory = os.path.dirname(file_info['file_path'])
        filename = os.path.basename(file_info['file_path'])
        return send_from_directory(directory, filename, as_attachment=True, download_name=file_info['file_name'])
    else:
        flash('File not found on server.', 'danger')
        return redirect(url_for('dashboard'))


@app.route('/files/view/<int:file_id>')
@login_required
def view_file(file_id):
    """View a lecture file (for PDFs and images)"""
    file_info = db.get_lecture_file_by_id(file_id)
    
    if not file_info:
        flash('File not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check access rights
    user_role = session.get('role')
    
    if user_role == 'student':
        student = db.get_student_by_user_id(session['user_id'])
        if student:
            # Check if student's class_id matches the file's class_id
            if student['class_id'] != file_info['class_id']:
                flash('Access denied. This file is not for your class.', 'danger')
                return redirect(url_for('student_files'))
    
    if os.path.exists(file_info['file_path']):
        directory = os.path.dirname(file_info['file_path'])
        filename = os.path.basename(file_info['file_path'])
        return send_from_directory(directory, filename)
    else:
        flash('File not found on server.', 'danger')
        return redirect(url_for('dashboard'))


# =============================================
# STUDENT - VIEW LECTURE FILES
# =============================================

@app.route('/student/files')
@login_required
def student_files():
    """View lecture files for student's class"""
    if session.get('role') != 'student':
        return redirect(url_for('dashboard'))
    
    student = db.get_student_by_user_id(session['user_id'])
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    files = []
    grouped_files = {}
    if student['class_id']:
        files = db.get_lecture_files_by_class(student['class_id']) or []
        # Group files by subject
        for file in files:
            subject_name = file['subject_name']
            if subject_name not in grouped_files:
                grouped_files[subject_name] = []
            grouped_files[subject_name].append(file)
    
    return render_template('student/files.html', files=files, grouped_files=grouped_files, student=student)


# =============================================
# INITIALIZE DEFAULT ADMIN
# =============================================

# =============================================
# ADMIN - SCHEDULE BUILDER API
# =============================================

@app.route('/admin/api/schedule/<int:semester>/<shift>/<section>', methods=['GET'])
@admin_required
def api_get_schedule(semester, shift, section):
    """API: Get schedule for a semester/shift/section"""
    import json
    schedule = db.get_schedule(semester, shift, section)
    if schedule and schedule.get('schedule_data'):
        data = schedule['schedule_data']
        # If it's already a list/dict, return as-is
        if isinstance(data, (list, dict)):
            return {'success': True, 'data': data}
        # If it's a string, parse it
        return {'success': True, 'data': json.loads(data)}
    return {'success': True, 'data': []}


@app.route('/admin/api/schedule/<int:semester>/<shift>/<section>', methods=['POST'])
@admin_required
def api_save_schedule(semester, shift, section):
    """API: Save schedule for a semester/shift/section"""
    import json
    data = request.get_json()
    schedule_data = data.get('schedule_data', [])
    
    result = db.save_schedule(semester, shift, section, json.dumps(schedule_data))
    if result:
        return {'success': True, 'message': 'Schedule saved successfully!'}
    return {'success': False, 'message': 'Error saving schedule'}, 500


@app.route('/admin/api/teachers-subjects/<int:semester>')
@admin_required
def api_get_teachers_subjects_by_semester(semester):
    """API: Get subjects for this semester + their teacher assignments"""
    conn = db.get_db_connection()
    if not conn:
        return {'subjects': [], 'assignments': []}
    
    cur = conn.cursor()
    
    try:
        # 1) Get all subjects for this semester
        cur.execute("""
            SELECT id, name, description
            FROM subjects
            WHERE semester = %s
            ORDER BY name
        """, (semester,))
        sem_subjects = cur.fetchall()
        
        print(f"Found {len(sem_subjects)} subjects for semester {semester}")
        
        # 2) Build subjects list
        subject_list = []
        for row in sem_subjects:
            subject_list.append({
                'id': row[0],
                'name': row[1],
                'description': row[2] or ''
            })
        
        # 3) Get actual teacher assignments from teacher_assignments table
        subject_ids = [s[0] for s in sem_subjects]
        assignment_list = []
        
        if subject_ids:
            cur.execute("""
                SELECT
                    ta.id,
                    ta.subject_id,
                    s.name,
                    ta.shift,
                    t.id,
                    u.full_name
                FROM teacher_assignments ta
                JOIN subjects s ON ta.subject_id = s.id
                JOIN teachers t ON ta.teacher_id = t.id
                JOIN users u ON t.user_id = u.id
                WHERE ta.subject_id = ANY(%s)
                ORDER BY s.name, ta.shift
            """, (subject_ids,))
            assignments = cur.fetchall()
            
            print(f"Found {len(assignments)} teacher assignments")
            
            # Build assignment list - expand to all sections (A, B, C) since assignments are per shift
            for row in assignments:
                # Each teacher assignment is for a shift, apply to all sections
                for section in ['A', 'B', 'C']:
                    assignment_list.append({
                        'assignment_id': row[0],
                        'subject_id': row[1],
                        'subject_name': row[2],
                        'shift': row[3] or '',
                        'section': section,
                        'teacher_id': row[4],
                        'teacher_name': row[5] or ''
                    })
        
        print(f"API Response: {len(subject_list)} subjects, {len(assignment_list)} assignment entries (expanded) for semester {semester}")
        
        return {
            'subjects': subject_list,
            'assignments': assignment_list
        }
        
    except Exception as e:
        print(f"ERROR in api_get_teachers_subjects_by_semester: {e}")
        import traceback
        traceback.print_exc()
        return {'subjects': [], 'assignments': [], 'error': str(e)}
    finally:
        cur.close()
        conn.close()


@app.route('/admin/api/teachers-subjects')
@admin_required
def api_get_teachers_subjects():
    """API: Get all teachers and subjects for schedule dropdown"""
    teachers = db.get_all_teachers() or []
    subjects = db.get_all_subjects() or []
    
    return {
        'teachers': [{'id': t['id'], 'name': t['full_name']} for t in teachers],
        'subjects': [{
            'id': s['id'], 
            'name': s['name'], 
            'semester': s.get('semester'), 
            'year': s.get('year'), 
            'teacher_name': s.get('teacher_name'),
            'practical_teacher_name': s.get('practical_teacher_name')
        } for s in subjects]
    }


def init_admin():
    """Create default admin user if not exists"""
    admin = db.get_user_by_username('admin')
    if not admin:
        password_hash = generate_password_hash('admin123')
        db.create_user('admin', password_hash, 'System Administrator', 'admin', 'admin@mis.edu', 'admin123')
        print("Default admin created. Username: admin, Password: admin123")
    # Ensure exam notes column exists
    db.ensure_exam_notes_column()


# =============================================
# AJAX ROUTES FOR MODAL EDITING
# =============================================

@app.route('/admin/users/<int:user_id>/edit-ajax', methods=['POST'])
@admin_required
def admin_edit_user_ajax(user_id):
    """Edit user via AJAX"""
    from flask import jsonify
    username = request.form.get('username', '').strip()
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    role = request.form.get('role', '').strip()
    new_password = request.form.get('new_password', '')
    
    if not username or not full_name or not role:
        return jsonify({'success': False, 'message': 'Username, full name, and role are required.'})
    
    # Check if username is being changed and if it exists
    current_user = db.get_user_by_id(user_id)
    if current_user and username != current_user['username']:
        existing = db.get_user_by_username(username)
        if existing:
            return jsonify({'success': False, 'message': 'Username already exists.'})
    
    # Validate password if provided
    if new_password:
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters long.'})
    
    # Update user with username and role
    result = db.update_user_complete(user_id, username, full_name, email, role)
    
    # Update password if provided
    plain_pass = None
    if new_password:
        password_hash = generate_password_hash(new_password)
        plain_pass = new_password
        password_result = db.update_user_password(user_id, password_hash, plain_pass)
        if password_result is None:
            return jsonify({'success': False, 'message': 'Error updating password.'})
    
    if result is not None:
        return jsonify({
            'success': True,
            'message': 'User updated successfully!' + (' Password changed.' if new_password else ''),
            'user': {
                'id': user_id,
                'username': username,
                'full_name': full_name,
                'email': email,
                'role': role,
                'plain_password': plain_pass if plain_pass else None
            }
        })
    return jsonify({'success': False, 'message': 'Error updating user.'})


@app.route('/admin/users/add-ajax', methods=['POST'])
@admin_required
def admin_add_user_ajax():
    """Add user via AJAX"""
    from flask import jsonify
    username = request.form.get('username', '').strip()
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    role = request.form.get('role', '').strip()
    password = request.form.get('password', '')
    
    if not username or not full_name or not role or not password:
        return jsonify({'success': False, 'message': 'Please fill in all required fields.'})
    
    # Check if username exists
    existing = db.get_user_by_username(username)
    if existing:
        return jsonify({'success': False, 'message': 'Username already exists.'})
    
    password_hash = generate_password_hash(password)
    user_id = db.create_user(username, password_hash, full_name, role, email, password)
    
    if user_id:
        # Fetch the newly created user to return full data
        new_user = db.get_user_by_id(user_id)
        if new_user:
            user_data = {
                'id': new_user['id'],
                'username': new_user['username'],
                'full_name': new_user['full_name'],
                'email': new_user.get('email'),
                'role': new_user['role'],
                'plain_password': new_user.get('plain_password')
            }
            
            # Add additional info based on role
            if role == 'teacher':
                teacher = db.get_teacher_by_user_id(user_id)
                if teacher:
                    subjects = db.get_subjects_by_teacher_id(teacher['id'])
                    user_data['subjects'] = ','.join([str(s['id']) for s in subjects]) if subjects else None
                    user_data['department'] = teacher.get('department')
            elif role == 'student':
                student = db.get_student_by_user_id(user_id)
                if student:
                    user_data['year'] = student.get('year')
                    user_data['semester'] = student.get('semester')
                    user_data['shift'] = student.get('shift')
                    user_data['section'] = student.get('section')
            
            return jsonify({'success': True, 'message': 'User created successfully!', 'user': user_data})
    
    return jsonify({'success': False, 'message': 'Error creating user.'})


@app.route('/admin/subjects/<int:subject_id>/edit-ajax', methods=['POST'])
@admin_required
def admin_edit_subject_ajax(subject_id):
    """Edit subject via AJAX"""
    from flask import jsonify
    try:
        name = request.form.get('name', '').strip()
        year = request.form.get('year', type=int)
        semester = request.form.get('semester', type=int)
        description = request.form.get('description', '').strip()
        credits = request.form.get('credits', type=int) or 6
        
        if not name or not semester:
            return jsonify({'success': False, 'message': 'Please enter subject name and select semester.'})
        
        if credits < 1 or credits > 30:
            return jsonify({'success': False, 'message': 'Credits must be between 1 and 30.'})
        
        result = db.update_subject(subject_id, name, semester, description, credits)
        
        if result is not None:
            return jsonify({
                'success': True,
                'message': 'Subject updated successfully!',
                'subject': {
                    'id': subject_id,
                    'name': name
                }
            })
        return jsonify({'success': False, 'message': 'Error updating subject.'})
    except Exception as e:
        print(f'Error in admin_edit_subject_ajax: {e}')
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})


@app.route('/admin/subjects/add-ajax', methods=['POST'])
@admin_required
def admin_add_subject_ajax():
    """Add subject via AJAX"""
    from flask import jsonify
    try:
        name = request.form.get('name', '').strip()
        year = request.form.get('year', type=int)
        semester = request.form.get('semester', type=int)
        description = request.form.get('description', '').strip()
        credits = request.form.get('credits', type=int) or 6
        
        if not name or not semester:
            return jsonify({'success': False, 'message': 'Please enter subject name and select semester.'})
        
        if credits < 1 or credits > 30:
            return jsonify({'success': False, 'message': 'Credits must be between 1 and 30.'})
        
        result = db.create_subject(name, semester, description, credits)
        
        if result:
            return jsonify({'success': True, 'message': 'Subject created successfully!'})
        return jsonify({'success': False, 'message': 'Subject already exists or error creating subject.'})
    except Exception as e:
        print(f'Error in admin_add_subject_ajax: {e}')
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})


# =============================================
# ADMIN - SEMESTER UPGRADE
# =============================================

@app.route('/admin/upgrade/preview/<int:semester>')
@admin_required
def admin_upgrade_preview(semester):
    """Show pass/fail preview for a semester before upgrading"""
    if semester < 1 or semester > 4:
        flash('Invalid semester.', 'danger')
        return redirect(url_for('admin_dashboard'))

    # Ensure table exists
    db.ensure_upgrade_tables()

    preview = db.get_semester_upgrade_preview(semester)
    return render_template('admin/upgrade_preview.html',
                         preview=preview,
                         semester=semester)


@app.route('/admin/upgrade/execute/<int:semester>', methods=['POST'])
@admin_required
def admin_upgrade_execute(semester):
    """Actually promote passing students"""
    if semester < 1 or semester > 4:
        flash('Invalid semester.', 'danger')
        return redirect(url_for('admin_dashboard'))

    db.ensure_upgrade_tables()

    try:
        result = db.execute_semester_upgrade(semester, session['user_id'])
        if semester >= 4:
            flash(f'Semester {semester} upgrade complete: {result["graduated"]} graduated, {result["failed"]} failed.', 'success')
        else:
            flash(f'Semester {semester} upgrade complete: {result["promoted"]} promoted to Semester {semester+1}, {result["failed"]} failed (stay in Semester {semester}).', 'success')
    except Exception as e:
        print(f'Error executing upgrade: {e}')
        flash(f'Error during upgrade: {str(e)}', 'danger')

    return redirect(url_for('admin_dashboard'))


# =============================================
# RUN APPLICATION
# =============================================

if __name__ == '__main__':
    init_admin()
    app.run(debug=True, host='0.0.0.0', port=5000)
