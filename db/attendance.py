from .core import *

def record_attendance(student_id, subject_id, teacher_id, date, status, notes=None): return execute_insert_returning("INSERT INTO attendance (student_id, subject_id, teacher_id, date, status, notes) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (student_id, subject_id, date) DO UPDATE SET status=EXCLUDED.status, notes=EXCLUDED.notes RETURNING id", (student_id, subject_id, teacher_id, date, status, notes))

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
