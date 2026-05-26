from .core import *

def get_semester_for_year(year, cycle=None):
    if cycle is None: cycle = get_current_cycle()
    return (1 if cycle == 1 else 2) if year == 1 else (3 if cycle == 1 else 4)

def get_exam_eligible_subjects(student_id, exam_type, semester=None):
    enrolled = get_enrolled_subjects_for_student(student_id) or []
    if semester: enrolled = [s for s in enrolled if s.get('semester') == semester]
    eligible = []
    if exam_type == 'final':
        for subj in enrolled:
            midterm = get_student_midterm_score(student_id, subj['id'])
            max_val, score = midterm['total_max'], midterm['total_score']
            normalized = score / max_val * 60 if max_val > 0 else 0
            existing = get_exam_signup(student_id, subj['id'], 'final')
            subj['midterm_score'] = round(score, 1)
            subj['midterm_max'] = round(max_val, 1)
            subj['midterm_normalized'] = round(normalized, 1)
            subj['coursework_score'] = round(score, 1)
            subj['coursework_max'] = round(max_val, 1)
            subj['coursework_normalized'] = round(normalized, 1)
            subj['already_signed_up'] = existing is not None
            subj['eligible'] = normalized >= 20
            eligible.append(subj)
    elif exam_type == 'second_round':
        for subj in enrolled:
            if not subj.get('results_published'): continue
            grades_data = get_student_result_grades_for_subject(student_id, subj['id']) or []
            if not grade_rows_have_scores(grades_data):
                continue
            total_score, total_max = _calc_grade_totals(grades_data)
            percentage = (total_score / total_max * 100) if total_max > 0 else 0
            if percentage >= 60: continue
            existing = get_exam_signup(student_id, subj['id'], 'second_round')
            subj['percentage'] = round(percentage, 1)
            subj['already_signed_up'] = existing is not None
            subj['eligible'] = True
            eligible.append(subj)
    return eligible

def get_exam_signups_for_subject(subject_id, exam_type=None):
    query = "SELECT es.*, u.full_name as student_name, st.student_number FROM exam_signups es JOIN students st ON es.student_id=st.id JOIN users u ON st.user_id=u.id WHERE es.subject_id=%s"
    params = [subject_id]
    if exam_type: query += " AND es.exam_type=%s"; params.append(exam_type)
    return execute_query(query+" ORDER BY u.full_name", tuple(params), fetch_all=True)

def create_subject(name, semester, description=None, credits=6, major_id=None):
    if major_id: existing = execute_query("SELECT id FROM subjects WHERE LOWER(name)=LOWER(%s) AND semester=%s AND major_id=%s", (name, semester, major_id), fetch_one=True)
    else: existing = execute_query("SELECT id FROM subjects WHERE LOWER(name)=LOWER(%s) AND semester=%s", (name, semester), fetch_one=True)
    if existing: return existing['id']
    return execute_insert_returning("INSERT INTO subjects (name, semester, description, credits, major_id) VALUES (%s,%s,%s,%s,%s) RETURNING id", (name, semester, description, credits, major_id))

def get_all_subjects(major_id=None):
    base = "SELECT DISTINCT s.*, c.name as class_name, c.year, c.semester, c.section, c.shift, ta.id as assignment_id, t.id as teacher_id, u.full_name as teacher_name FROM subjects s LEFT JOIN teacher_assignments ta ON s.id=ta.subject_id LEFT JOIN classes c ON ta.class_id=c.id LEFT JOIN teachers t ON ta.teacher_id=t.id LEFT JOIN users u ON t.user_id=u.id"
    if major_id: return execute_query(base+" WHERE s.major_id=%s ORDER BY s.name, c.year, c.semester, c.section", (major_id,), fetch_all=True)
    return execute_query(base+" ORDER BY s.name, c.year, c.semester, c.section", fetch_all=True)

def get_unique_subjects_by_semester(major_id=None):
    if major_id: return execute_query("SELECT DISTINCT s.name, CASE WHEN s.semester IN (1,2) THEN 1 ELSE 2 END AS year, s.semester FROM subjects s WHERE s.semester IS NOT NULL AND s.major_id=%s ORDER BY s.semester, s.name", (major_id,), fetch_all=True)
    return execute_query("SELECT DISTINCT s.name, CASE WHEN s.semester IN (1,2) THEN 1 ELSE 2 END AS year, s.semester FROM subjects s WHERE s.semester IS NOT NULL ORDER BY s.semester, s.name", fetch_all=True)

def get_subjects_grouped_by_semester(major_id=None):
    major_filter = "AND s.major_id = %s" if major_id else ""
    query = f"""SELECT s.id, s.name, s.semester, s.description, s.credits, s.results_published, c.year, c.section,
        ta.id as assignment_id, t.id as teacher_id, u.full_name as teacher_name,
        COALESCE(gw.total_weight,0) AS total_weight, COALESCE(gw.component_count,0) AS component_count
        FROM subjects s LEFT JOIN teacher_assignments ta ON s.id=ta.subject_id LEFT JOIN classes c ON ta.class_id=c.id
        LEFT JOIN teachers t ON ta.teacher_id=t.id LEFT JOIN users u ON t.user_id=u.id
        LEFT JOIN (SELECT subject_id, COUNT(*) AS component_count, SUM(weight_percentage) AS total_weight FROM grade_components GROUP BY subject_id) gw ON s.id=gw.subject_id
        WHERE s.semester IS NOT NULL {major_filter} ORDER BY c.year, s.semester, c.section, s.name"""
    return execute_query(query, (major_id,) if major_id else None, fetch_all=True)

def get_semesters():
    return [{'year':1,'semester':1,'name':'Year 1 - Semester 1'},{'year':1,'semester':2,'name':'Year 1 - Semester 2'},{'year':2,'semester':3,'name':'Year 2 - Semester 3'},{'year':2,'semester':4,'name':'Year 2 - Semester 4'}]

def get_subject_by_id(subject_id): return execute_query("SELECT s.*, s.semester as semester, ta.id as assignment_id, ta.class_id, c.year, c.section, c.shift, t.id as teacher_id, u.full_name as teacher_name FROM subjects s LEFT JOIN teacher_assignments ta ON s.id=ta.subject_id LEFT JOIN classes c ON ta.class_id=c.id LEFT JOIN teachers t ON ta.teacher_id=t.id LEFT JOIN users u ON t.user_id=u.id WHERE s.id=%s", (subject_id,), fetch_one=True)

def update_subject(subject_id, name, semester, description=None, credits=6): return execute_query("UPDATE subjects SET name=%s, semester=%s, description=%s, credits=%s WHERE id=%s", (name, semester, description, credits, subject_id))

def delete_subject(subject_id): return execute_query("DELETE FROM subjects WHERE id=%s", (subject_id,))

def get_attendance_by_subject_date(subject_id, date): return execute_query("SELECT a.*, u.full_name as student_name, st.student_number FROM attendance a JOIN students st ON a.student_id=st.id JOIN users u ON st.user_id=u.id WHERE a.subject_id=%s AND a.date=%s ORDER BY u.full_name", (subject_id, date), fetch_all=True)

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

def publish_grades_for_subject(subject_id, class_id):
    """Publish all draft grades for a specific subject and class"""
    if class_id:
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
    else:
        # No class assignment — publish all grades for this subject
        query = """
            UPDATE grades 
            SET published = TRUE
            WHERE subject_id = %s 
            AND published = FALSE
        """
        return execute_query(query, (subject_id,))

def toggle_subject_results_published(subject_id, published, major_id=None):
    """Admin: Toggle results visibility for a subject (final transcript)"""
    ensure_results_publication_support()
    query = """
        UPDATE subjects 
        SET results_published = %s,
            results_published_at = CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE NULL END
        WHERE id = %s
    """
    params = [published, published, subject_id]
    if major_id is not None:
        query += " AND major_id = %s"
        params.append(major_id)
    return execute_query(query, tuple(params))

def publish_semester_results(semester, major_id=None):
    """Admin: Publish all subject results for an entire semester"""
    ensure_results_publication_support()
    query = """
        UPDATE subjects 
        SET results_published = TRUE,
            results_published_at = CURRENT_TIMESTAMP
        WHERE semester = %s
    """
    params = [semester]
    if major_id is not None:
        query += " AND major_id = %s"
        params.append(major_id)
    return execute_query(query, tuple(params))

def unpublish_semester_results(semester, major_id=None):
    """Admin: Close/unpublish all subject results for an entire semester"""
    ensure_results_publication_support()
    query = """
        UPDATE subjects 
        SET results_published = FALSE,
            results_published_at = NULL
        WHERE semester = %s
    """
    params = [semester]
    if major_id is not None:
        query += " AND major_id = %s"
        params.append(major_id)
    return execute_query(query, tuple(params))

def get_grade_components_by_subject(subject_id):
    """Get all grade components for a subject, ordered by display_order"""
    key = f'gc:{subject_id}'
    cached = _cache_get(key)
    if cached is not None:
        return cached
    query = """
        SELECT * FROM grade_components
        WHERE subject_id = %s
        ORDER BY display_order, component_type, id
    """
    result = execute_query(query, (subject_id,), fetch_all=True)
    _cache_set(key, result, CACHE_TTL)
    return result

def get_subject_total_weight(subject_id):
    """Calculate effective total weight for a subject.
    Paired components (same pair_group) count as ONE component's weight."""
    query = """
        SELECT COALESCE(SUM(weight_percentage), 0) AS total_weight
        FROM (
            SELECT weight_percentage,
                   ROW_NUMBER() OVER (
                       PARTITION BY CASE WHEN pair_group IS NULL THEN id::text
                                         ELSE (subject_id::text || '-' || pair_group::text) END
                       ORDER BY id
                   ) AS rn
            FROM grade_components
            WHERE subject_id = %s
        ) sub
        WHERE rn = 1
    """
    result = execute_query(query, (subject_id,), fetch_one=True)
    return float(result['total_weight']) if result else 0.0

def get_weekly_topics_by_subject(subject_id):
    """Get exam/quiz notes for a subject ordered by date"""
    query = """
        SELECT wt.*, u.full_name as teacher_name,
               COALESCE(wt.note_type, 'exam') as note_type
        FROM weekly_topics wt
        LEFT JOIN teachers t ON wt.teacher_id = t.id
        LEFT JOIN users u ON t.user_id = u.id
        WHERE wt.subject_id = %s
        ORDER BY wt.date_covered ASC NULLS LAST, wt.id DESC
    """
    return execute_query(query, (subject_id,), fetch_all=True)

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

def get_all_departments():
    """Get all colleges/departments (grouping layer, read-only)."""
    cached = _cache_get('departments:all')
    if cached is not None:
        return cached
    query = "SELECT * FROM departments ORDER BY name"
    result = execute_query(query, fetch_all=True)
    _cache_set('departments:all', result, CACHE_TTL_LONG)
    return result

def get_all_majors(department_id=None):
    """Get all majors, optionally filtered by college/department."""
    cached_key = f'majors:all:{department_id}'
    cached = _cache_get(cached_key)
    if cached is not None:
        return cached
    if department_id:
        query = """
            SELECT m.*, d.name AS college_name, d.code AS college_code,
                   (SELECT COUNT(*) FROM users u WHERE u.major_id = m.id) AS user_count
            FROM majors m
            LEFT JOIN departments d ON m.department_id = d.id
            WHERE m.department_id = %s
            ORDER BY m.name
        """
        result = execute_query(query, (department_id,), fetch_all=True)
    else:
        query = """
            SELECT m.*, d.name AS college_name, d.code AS college_code,
                   (SELECT COUNT(*) FROM users u WHERE u.major_id = m.id) AS user_count
            FROM majors m
            LEFT JOIN departments d ON m.department_id = d.id
            ORDER BY d.name, m.name
        """
        result = execute_query(query, fetch_all=True)
    _cache_set(cached_key, result, CACHE_TTL_LONG)
    return result

def get_major_by_id(major_id):
    """Get a single major by ID."""
    query = """
        SELECT m.*, d.name AS college_name, d.code AS college_code
        FROM majors m
        LEFT JOIN departments d ON m.department_id = d.id
        WHERE m.id = %s
    """
    return execute_query(query, (major_id,), fetch_one=True)

def get_major_by_code(code):
    """Get a major by its 6-digit numeric code."""
    query = """
        SELECT m.*, d.name AS college_name, d.code AS college_code
        FROM majors m
        LEFT JOIN departments d ON m.department_id = d.id
        WHERE m.code = %s
    """
    return execute_query(query, (str(code),), fetch_one=True)

def get_majors_with_admin_status():
    """Get all majors with count of admin users and their names (for superadmin UI)."""
    query = """
        SELECT m.*, d.name AS college_name, d.code AS college_code,
               COUNT(u.id) FILTER (WHERE u.role = 'admin') AS admin_count,
               STRING_AGG(u.full_name, ', ') FILTER (WHERE u.role = 'admin') AS admin_names
        FROM majors m
        LEFT JOIN departments d ON m.department_id = d.id
        LEFT JOIN users u ON u.major_id = m.id AND u.role = 'admin'
        GROUP BY m.id, d.name, d.code
        ORDER BY d.name, m.name
    """
    return execute_query(query, fetch_all=True)

def get_semester_upgrade_preview(semester, major_id=None):
    """Calculate pass/fail for every student in a semester.
    A student passes only if they score >= 60% in EVERY enrolled subject.
    Returns dict with 'passed' and 'failed' student lists.
    """
    # All students in this semester
    students_query = """
        SELECT s.id, s.shift, s.section, s.year, u.full_name, s.student_number
        FROM students s
        JOIN users u ON s.user_id = u.id
        WHERE s.semester = %s
    """
    params = [semester]
    if major_id is not None:
        students_query += " AND u.major_id = %s"
        params.append(major_id)
    students_query += " ORDER BY u.full_name"
    students = execute_query(students_query, tuple(params), fetch_all=True) or []

    passed = []
    failed = []

    for stu in students:
        # Enrolled subjects
        enrolled = execute_query("""
            SELECT sub.id, sub.name, sub.credits, sub.results_published, sub.results_published_at
            FROM student_enrollments se
            JOIN subjects sub ON se.subject_id = sub.id
            WHERE se.student_id = %s
              AND sub.semester = %s
        """ + (" AND sub.major_id = %s" if major_id is not None else ""), ((stu['id'], semester, major_id) if major_id is not None else (stu['id'], semester)), fetch_all=True) or []

        if not enrolled:
            # No enrollments - cannot evaluate - mark as failed
            failed.append({**dict(stu), 'subjects': [], 'reason': 'No enrollments'})
            continue

        subject_results = []
        all_passed = True

        for subj in enrolled:
            if subj.get('results_published') and subj.get('results_published_at'):
                grades = get_student_result_grades_for_subject(stu['id'], subj['id']) or []
            else:
                grades = get_student_grades_for_subject(stu['id'], subj['id']) or []

            if not grade_rows_have_scores(grades):
                subject_results.append({'name': subj['name'], 'percentage': 0, 'passed': False})
                all_passed = False
                continue

            total_score, total_max = _calc_grade_totals(grades)

            pct = (total_score / total_max * 100) if total_max > 0 else 0
            subj_passed = pct >= 60
            subject_results.append({
                'name': subj['name'],
                'percentage': round(pct, 1),
                'passed': subj_passed
            })
            if not subj_passed:
                all_passed = False

        entry = {**dict(stu), 'subjects': subject_results}
        if all_passed:
            passed.append(entry)
        else:
            failed.append(entry)

    return {'passed': passed, 'failed': failed, 'semester': semester}
