import sys

def main():
    content = open('db.py', 'r', encoding='utf-8').read()
    if 'def get_enrollment_period_signup_summary' in content:
        return
    start = content.find('def get_exam_period_signup_summary')
    end = content.find('def ', start + 30)
    
    new_func = '''
def get_enrollment_period_signup_summary(semester, major_id=None):
    """Summarize which students in a semester have enrolled in at least one subject."""
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
            SELECT se.student_id,
                   COUNT(*) AS signup_count
            FROM student_enrollments se
            JOIN subjects sub ON sub.id = se.subject_id
            WHERE sub.semester = %s
            GROUP BY se.student_id
        )
        SELECT ss.*,
               COALESCE(sc.signup_count, 0) AS signup_count,
               CASE WHEN COALESCE(sc.signup_count, 0) > 0 THEN TRUE ELSE FALSE END AS is_assigned
        FROM semester_students ss
        LEFT JOIN signup_counts sc ON sc.student_id = ss.student_id
    """
    params = [semester, semester]
    if major_id is not None:
        query = query.replace("WHERE st.semester = %s", "WHERE st.semester = %s AND u.major_id = %s")
        params = [semester, major_id, semester]
    query += " ORDER BY is_assigned DESC, ss.full_name"
    rows = execute_query(query, tuple(params), fetch_all=True) or []
    assigned = [row for row in rows if row.get('is_assigned')]
    pending = [row for row in rows if not row.get('is_assigned')]
    return {
        'total_students': len(rows),
        'assigned_count': len(assigned),
        'pending_count': len(pending),
        'assigned': assigned,
        'pending': pending,
        'all_rows': rows
    }

'''
    updated = content[:end] + new_func + content[end:]
    open('db.py', 'w', encoding='utf-8').write(updated)
    print("Injected successfully!")

if __name__ == '__main__':
    main()
