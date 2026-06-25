from .core import *
from .core import _cache_delete, _summarize_component_rows
from .upgrade import ensure_file_metadata_support, ensure_moodle_assignment_support

_results_schema_ready = False
_exam_signup_status_ready = False


def ensure_exam_signup_status_support():
    """Ensure exam_signups has a status column ('enrolled'|'dropped') and action_taken_at."""
    global _exam_signup_status_ready
    if _exam_signup_status_ready:
        return

    conn = get_db_connection()
    if not conn:
        raise RuntimeError('Database connection unavailable')

    try:
        cursor = conn.cursor()
        cursor.execute("""
            ALTER TABLE exam_signups
            ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'enrolled'
        """)
        cursor.execute("""
            ALTER TABLE exam_signups
            ADD COLUMN IF NOT EXISTS action_taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """)
        # Back-fill any existing rows with no status
        cursor.execute("""
            UPDATE exam_signups
            SET action_taken_at = COALESCE(action_taken_at, signed_up_at, CURRENT_TIMESTAMP)
            WHERE action_taken_at IS NULL
        """)
        conn.commit()
        cursor.close()
        return_connection(conn)
        _exam_signup_status_ready = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return_connection(conn)
        raise

def ensure_results_publication_support():
    """Ensure result-publication snapshot columns exist."""
    global _results_schema_ready
    if _results_schema_ready:
        return

    conn = get_db_connection()
    if not conn:
        raise RuntimeError('Database connection unavailable')

    try:
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE subjects ADD COLUMN IF NOT EXISTS results_published_at TIMESTAMP")
        cursor.execute("ALTER TABLE grades ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")
        cursor.execute("ALTER TABLE grades ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP")
        cursor.execute("""
            UPDATE subjects
            SET results_published_at = CURRENT_TIMESTAMP
            WHERE results_published = TRUE
              AND results_published_at IS NULL
        """)
        cursor.execute("""
            UPDATE grades
            SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
            WHERE updated_at IS NULL
        """)
        conn.commit()
        cursor.close()
        return_connection(conn)
        _results_schema_ready = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return_connection(conn)
        raise

def grade_rows_have_scores(rows):
    """Return True when at least one grade row has a real saved score."""
    return any(row.get('score') is not None for row in (rows or []))

def create_exam_period(semester, period_type, start_date, end_date, description, created_by): return execute_insert_returning("INSERT INTO exam_periods (semester, period_type, start_date, end_date, description, created_by) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id", (semester, period_type, start_date, end_date, description, created_by))

def get_all_exam_periods(semester=None, major_id=None):
    query = "SELECT ep.*, u.full_name as created_by_name FROM exam_periods ep LEFT JOIN users u ON ep.created_by=u.id WHERE 1=1"
    params = []
    if semester: query += " AND ep.semester=%s"; params.append(semester)
    if major_id: query += " AND u.major_id=%s"; params.append(major_id)
    return execute_query(query+" ORDER BY ep.semester, ep.period_type, ep.created_at DESC", tuple(params) if params else None, fetch_all=True)

def get_active_exam_period(semester, period_type, major_id=None):
    query = "SELECT ep.* FROM exam_periods ep LEFT JOIN users u ON ep.created_by=u.id WHERE ep.semester=%s AND ep.period_type=%s AND %s BETWEEN ep.start_date AND ep.end_date"
    params = [semester, period_type, datetime.now()]
    if major_id: query += " AND u.major_id=%s"; params.append(major_id)
    return execute_query(query+" ORDER BY ep.created_at DESC LIMIT 1", tuple(params), fetch_one=True)

def get_exam_period_signup_summary(semester, period_type, major_id=None):
    """Summarize which students in a semester have signed up for at least one exam of a given type."""
    ensure_exam_signup_status_support()
    query = """
        WITH semester_students AS (
            SELECT st.id AS student_id,
                   u.full_name AS student_name,
                   u.username,
                   st.student_number,
                   st.shift,
                   st.section,
                   c.name AS class_name
            FROM students st
            JOIN users u ON u.id = st.user_id
            LEFT JOIN classes c ON c.id = st.class_id
            WHERE st.semester = %s
        ),
        signup_counts AS (
            SELECT es.student_id,
                   COUNT(CASE WHEN es.status = 'enrolled' THEN 1 END) AS enrolled_count,
                   COUNT(CASE WHEN es.status = 'dropped' THEN 1 END) AS dropped_count
            FROM exam_signups es
            JOIN subjects sub ON sub.id = es.subject_id
            WHERE es.exam_type = %s
              AND sub.semester = %s
            GROUP BY es.student_id
        )
        SELECT ss.*,
               COALESCE(sc.enrolled_count, 0) AS enrolled_count,
               COALESCE(sc.dropped_count, 0) AS dropped_count,
               COALESCE(sc.enrolled_count, 0) AS signup_count,
               CASE WHEN COALESCE(sc.enrolled_count, 0) > 0 THEN 'enrolled'
                    WHEN COALESCE(sc.dropped_count, 0) > 0 THEN 'dropped'
                    ELSE 'pending' END AS signup_status,
               CASE WHEN COALESCE(sc.enrolled_count, 0) > 0 THEN TRUE ELSE FALSE END AS is_assigned
        FROM semester_students ss
        LEFT JOIN signup_counts sc ON sc.student_id = ss.student_id
    """
    params = [semester, period_type, semester]
    if major_id is not None:
        query = query.replace("WHERE st.semester = %s", "WHERE st.semester = %s AND u.major_id = %s")
        params = [semester, major_id, period_type, semester]
    query += " ORDER BY is_assigned DESC, ss.student_name"
    rows = execute_query(query, tuple(params), fetch_all=True) or []
    enrolled = [row for row in rows if row.get('signup_status') == 'enrolled']
    dropped  = [row for row in rows if row.get('signup_status') == 'dropped']
    pending  = [row for row in rows if row.get('signup_status') == 'pending']
    return {
        'total_students': len(rows),
        'enrolled_count': len(enrolled),
        'dropped_count':  len(dropped),
        'pending_count':  len(pending),
        'assigned_count': len(enrolled),
        'assigned_students': enrolled,
        'pending_students': pending,
        'students': rows,
    }

def delete_exam_period(period_id): return execute_query("DELETE FROM exam_periods WHERE id=%s", (period_id,))


def signup_for_exam(student_id, subject_id, exam_type):
    """Sign a student up for an exam — sets status='enrolled'. Uses upsert to re-activate if previously dropped."""
    ensure_exam_signup_status_support()
    return execute_insert_returning(
        """INSERT INTO exam_signups (student_id, subject_id, exam_type, status, action_taken_at)
           VALUES (%s, %s, %s, 'enrolled', CURRENT_TIMESTAMP)
           ON CONFLICT (student_id, subject_id, exam_type)
           DO UPDATE SET status = 'enrolled', action_taken_at = CURRENT_TIMESTAMP
           RETURNING id""",
        (student_id, subject_id, exam_type)
    )


def drop_exam_signup(student_id, subject_id, exam_type):
    """Drop a student from an exam — sets status='dropped'. Preserves the row for admin audit trail."""
    ensure_exam_signup_status_support()
    return execute_query(
        """UPDATE exam_signups
           SET status = 'dropped', action_taken_at = CURRENT_TIMESTAMP
           WHERE student_id = %s AND subject_id = %s AND exam_type = %s""",
        (student_id, subject_id, exam_type)
    )


def cancel_exam_signup(student_id, subject_id, exam_type):
    """Alias kept for backward compatibility — now calls drop_exam_signup."""
    return drop_exam_signup(student_id, subject_id, exam_type)


def get_exam_signup(student_id, subject_id, exam_type):
    """Return the exam signup row (any status) for a student+subject+exam_type."""
    ensure_exam_signup_status_support()
    return execute_query(
        "SELECT * FROM exam_signups WHERE student_id=%s AND subject_id=%s AND exam_type=%s",
        (student_id, subject_id, exam_type), fetch_one=True
    )

def add_grade(student_id, subject_id, teacher_id, grade_type, title, score, max_score, date, notes=None, component_id=None, published=False):
    """Add a grade for a student (default unpublished/draft)"""
    ensure_results_publication_support()
    query = """
        INSERT INTO grades (student_id, subject_id, teacher_id, grade_type, title, score, max_score, date, notes, component_id, published, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        RETURNING id
    """
    return execute_insert_returning(query, (student_id, subject_id, teacher_id, grade_type, title, score, max_score, date, notes, component_id, published))

def upsert_grade(student_id, subject_id, teacher_id, grade_type, title, score, max_score, date, component_id, notes=None, published=False):
    """Update existing grade or insert new one for a student/component combination (default unpublished/draft)"""
    ensure_results_publication_support()
    # Check if a grade already exists for this student and component
    check_query = """
        SELECT id FROM grades 
        WHERE student_id = %s AND component_id = %s
        ORDER BY date DESC, id DESC
        LIMIT 1
    """
    existing = execute_query(check_query, (student_id, component_id), fetch_one=True)

    if existing:
        update_query = """
            UPDATE grades 
            SET score = %s, max_score = %s, date = %s, notes = %s, grade_type = %s, title = %s,
                published = CASE WHEN published = TRUE THEN TRUE ELSE %s END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id
        """
        return execute_insert_returning(update_query, (score, max_score, date, notes, grade_type, title, published, existing['id']))
    else:
        insert_query = """
            INSERT INTO grades (student_id, subject_id, teacher_id, grade_type, title, score, max_score, date, notes, component_id, published, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING id
        """
        return execute_insert_returning(insert_query, (student_id, subject_id, teacher_id, grade_type, title, score, max_score, date, notes, component_id, published))

def get_unpublished_grade_count(subject_id, class_id):
    """Get count of unpublished grades for a subject/class"""
    if class_id:
        query = """
            SELECT COUNT(*) as count
            FROM grades g
            JOIN students s ON g.student_id = s.id
            WHERE g.subject_id = %s 
            AND s.class_id = %s
            AND g.published = FALSE
        """
        result = execute_query(query, (subject_id, class_id), fetch_one=True)
    else:
        query = """
            SELECT COUNT(*) as count
            FROM grades g
            WHERE g.subject_id = %s 
            AND g.published = FALSE
        """
        result = execute_query(query, (subject_id,), fetch_one=True)
    return result['count'] if result else 0

def create_homework(class_id, subject_id, teacher_id, title, description, due_date,
                    filename=None, file_path=None, file_type=None, file_size=None,
                    week_id=None, is_moodle_request=False, due_at=None):
    """Create a new homework assignment"""
    ensure_file_metadata_support()
    ensure_moodle_assignment_support()
    filename = filename or ""
    file_path = file_path or ""
    file_type = file_type or ""
    file_size = file_size or 0

    if isinstance(due_date, datetime):
        due_at = due_date
        due_date = due_date.date()
    elif due_at is None and due_date:
        due_at = f"{due_date} 23:59:00"

    query = """
        INSERT INTO homework (
            class_id, subject_id, teacher_id, title, description, due_date,
            filename, file_path, file_type, file_size, week_id, due_at, is_moodle_request
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (
        class_id, subject_id, teacher_id, title, description, due_date,
        filename, file_path, file_type, file_size, week_id, due_at, is_moodle_request
    ))

def delete_homework(homework_id, teacher_id):
    """Delete homework (mark as done) - only the teacher who created it can delete"""
    query = """
        DELETE FROM homework
        WHERE id = %s AND teacher_id = %s
        RETURNING id
    """
    return execute_insert_returning(query, (homework_id, teacher_id))

def _normalize_grade_component_type(component_type):
    return (component_type or '').lower().strip()

def _grade_component_label(component_type):
    return _normalize_grade_component_type(component_type).replace('_', ' ').title()

def _safe_grade_number(value):
    return float(value or 0)

def build_grade_summary(rows):
    """Build canonical grade summary and totals for all grade views.

    Rules:
      - Split midterm components are summed.
      - Non-paired quiz/homework/etc. components are averaged by category.
      - Paired categories (report + seminar) sum each side first, then the pair
        counts once as the average of those per-type totals.
    """
    raw_rows = list(rows or [])
    ordered_groups = []
    group_map = {}

    for row in raw_rows:
        item = row.copy() if isinstance(row, dict) else dict(row)
        component_type = _normalize_grade_component_type(item.get('component_type'))
        pair_group = item.get('pair_group')
        item['component_type'] = component_type

        if pair_group is not None:
            group_key = ('pair', pair_group)
            if group_key not in group_map:
                group_map[group_key] = {
                    'pair_group': pair_group,
                    'rows': [],
                    'type_rows': {},
                    'type_order': [],
                }
                ordered_groups.append(group_key)

            group = group_map[group_key]
            group['rows'].append(item)
            if component_type not in group['type_rows']:
                group['type_rows'][component_type] = []
                group['type_order'].append(component_type)
            group['type_rows'][component_type].append(item)
            continue

        group_key = ('single', component_type)
        if group_key not in group_map:
            group_map[group_key] = {
                'component_type': component_type,
                'rows': [],
            }
            ordered_groups.append(group_key)
        group_map[group_key]['rows'].append(item)

    total_score = 0.0
    total_max = 0.0
    display_groups = []

    for group_key in ordered_groups:
        group = group_map[group_key]

        if group_key[0] == 'pair':
            type_totals = []
            pair_scores = []
            pair_maxes = []

            for component_type in group['type_order']:
                type_rows = group['type_rows'][component_type]
                type_score, type_max = _summarize_component_rows(type_rows, force_sum=True)
                pair_scores.append(type_score)
                pair_maxes.append(type_max)
                type_totals.append({
                    'component_type': component_type,
                    'label': _grade_component_label(component_type),
                    'rows': type_rows,
                    'subtotal_score': round(type_score, 1),
                    'subtotal_max': round(type_max, 1),
                })

            type_count = len(type_totals)
            pair_score = (sum(pair_scores) / type_count) if type_count else 0.0
            pair_max = (sum(pair_maxes) / type_count) if type_count else 0.0

            total_score += pair_score
            total_max += pair_max
            display_groups.append({
                'is_paired': True,
                'label': 'Paired Average',
                'pair_group': group['pair_group'],
                'rows': group['rows'],
                'type_totals': type_totals,
                'subtotal_score': round(pair_score, 1),
                'subtotal_max': round(pair_max, 1),
            })
            continue

        component_type = group['component_type']
        subtotal_score, subtotal_max = _summarize_component_rows(
            group['rows'],
            force_sum=component_type in {'midterm'}
        )

        total_score += subtotal_score
        total_max += subtotal_max
        display_groups.append({
            'is_paired': False,
            'label': _grade_component_label(component_type),
            'component_type': component_type,
            'rows': group['rows'],
            'subtotal_score': round(subtotal_score, 1),
            'subtotal_max': round(subtotal_max, 1),
        })

    return {
        'groups': display_groups,
        'total_score': round(total_score, 1),
        'total_max': round(total_max, 1),
    }

def build_grade_display_groups(rows):
    """Return canonical display groups for grade tables."""
    return build_grade_summary(rows)['groups']

def _calc_grade_totals(rows):
    """Return canonical total score / total max for a grade component set."""
    summary = build_grade_summary(rows)
    return summary['total_score'], summary['total_max']

def add_grade_component(subject_id, component_type, component_name, max_score, weight_percentage, display_order=0, pair_group=None):
    """Add a grade component to a subject's grading rubric"""
    query = """
        INSERT INTO grade_components 
        (subject_id, component_type, component_name, max_score, weight_percentage, display_order, pair_group)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    result = execute_insert_returning(query, (subject_id, component_type, component_name, max_score, weight_percentage, display_order, pair_group))
    _cache_delete(f'gc:{subject_id}')
    return result

def update_grade_component(component_id, component_type, component_name, max_score, weight_percentage, display_order):
    """Update an existing grade component"""
    comp = execute_query("SELECT subject_id FROM grade_components WHERE id = %s", (component_id,), fetch_one=True)
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
    result = execute_insert_returning(query, (component_type, component_name, max_score, weight_percentage, display_order, component_id))
    if comp:
        _cache_delete(f'gc:{comp["subject_id"]}')
    return result

def delete_grade_component(component_id):
    """Delete a grade component"""
    comp = execute_query("SELECT subject_id FROM grade_components WHERE id = %s", (component_id,), fetch_one=True)
    query = "DELETE FROM grade_components WHERE id = %s RETURNING id"
    result = execute_insert_returning(query, (component_id,))
    if comp:
        _cache_delete(f'gc:{comp["subject_id"]}')
    return result

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

def ensure_exam_notes_column():
    """Add note_type column to weekly_topics if it doesn't exist"""
    try:
        execute_query("""
            ALTER TABLE weekly_topics
            ADD COLUMN IF NOT EXISTS note_type VARCHAR(20) DEFAULT 'exam'
        """, fetch_all=False)
    except Exception as e:
        print(f"ensure_exam_notes_column: {e}")

def create_exam_note(class_id, subject_id, teacher_id, note_type, title, description=None, exam_date=None):
    """Create an exam/quiz/report note (replaces create_weekly_topic)"""
    # Use max+1 as sequence so each insert is unique
    seq_row = execute_query(
        "SELECT COALESCE(MAX(week_number), 0) AS mx FROM weekly_topics WHERE subject_id = %s",
        (subject_id,), fetch_one=True
    )
    seq = (seq_row['mx'] if seq_row else 0) + 1
    query = """
        INSERT INTO weekly_topics
            (class_id, subject_id, teacher_id, week_number, topic, description, date_covered, note_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    return execute_insert_returning(query, (class_id, subject_id, teacher_id, seq, title, description, exam_date, note_type))

def delete_exam_note(note_id, teacher_id):
    """Delete an exam note by id (teacher must own it)"""
    execute_query(
        "DELETE FROM weekly_topics WHERE id = %s AND teacher_id = %s",
        (note_id, teacher_id), fetch_all=False
    )

def get_homework_for_week(week_id):
    ensure_moodle_assignment_support()
    query = """
        SELECT *
        FROM homework
        WHERE week_id = %s
          AND COALESCE(is_moodle_request, FALSE) = TRUE
        ORDER BY id ASC
    """
    return execute_query(query, (week_id,), fetch_all=True) or []

def delete_homework_by_week(week_id):
    ensure_moodle_assignment_support()
    query = "DELETE FROM homework WHERE week_id = %s AND COALESCE(is_moodle_request, FALSE) = TRUE"
    return execute_query(query, (week_id,))
