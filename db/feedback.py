from .core import *

def get_latest_feedback_period(major_id=None):
    """Finds the most recent study_year and semester to treat as 'current'"""
    query = "SELECT study_year, semester FROM feedback_forms"
    params = []
    if major_id:
        query += " WHERE created_by IN (SELECT id FROM users WHERE major_id = %s)"
        params.append(major_id)
    query += " ORDER BY created_at DESC LIMIT 1"
    
    row = execute_query(query, tuple(params) if params else None, fetch_one=True)
    if row:
        return {'study_year': row['study_year'], 'semester': row['semester']}
    return {'study_year': None, 'semester': None}

def get_feedback_summary(major_id=None):
    """Get main results view: Teachers with Current Avg and All-Time Avg"""
    import json
    
    period = get_latest_feedback_period(major_id)
    curr_year = period['study_year']
    curr_sem = period['semester']
    
    query = """
        SELECT 
            u.id as teacher_id, 
            u.full_name as teacher_name,
            f.study_year,
            f.semester,
            jsonb_agg(r.ratings) as all_ratings
        FROM feedback_responses r
        JOIN teachers t ON r.teacher_id = t.id
        JOIN users u ON t.user_id = u.id
        JOIN feedback_forms f ON r.form_id = f.id
    """
    params = []
    if major_id:
        query += " WHERE u.major_id = %s "
        params.append(major_id)
        
    query += " GROUP BY u.id, u.full_name, f.study_year, f.semester ORDER BY u.full_name"
    rows = execute_query(query, tuple(params) if params else None, fetch_all=True) or []
    
    teachers = {}
    for r in rows:
        tid = r['teacher_id']
        if tid not in teachers:
            teachers[tid] = {
                'teacher_id': tid,
                'teacher_name': r['teacher_name'],
                'current_score': 0, 'current_count': 0,
                'all_time_score': 0, 'all_time_count': 0
            }
            
        t = teachers[tid]
        score = 0
        count = 0
        
        all_rat = r.pop('all_ratings')
        if all_rat:
            for rtgs in all_rat:
                if type(rtgs) == str:
                    rtgs = json.loads(rtgs)
                if rtgs and isinstance(rtgs, dict):
                    for v in rtgs.values():
                        if str(v).isdigit():
                            score += int(v)
                            count += 1
                elif rtgs and isinstance(rtgs, list):
                    for v in rtgs:
                        if str(v).isdigit():
                            score += int(v)
                            count += 1
                            
        t['all_time_score'] += score
        t['all_time_count'] += count
        
        if r['study_year'] == curr_year:
            t['current_score'] += score
            t['current_count'] += count
            
    # Compute averages
    for t in teachers.values():
        t['current_avg'] = round(t['current_score'] / t['current_count'], 2) if t['current_count'] > 0 else "N/A"
        t['all_time_avg'] = round(t['all_time_score'] / t['all_time_count'], 2) if t['all_time_count'] > 0 else "N/A"
        
    return list(teachers.values())

def get_feedback_study_years(major_id=None):
    """Get list of distinct study years from feedback forms, optionally filtered by major.
    Since forms don't have major_id directly, we find forms where respondents belong to the major,
    or we just return all study years from the forms."""
    query = """
        SELECT DISTINCT f.study_year
        FROM feedback_forms f
        WHERE f.study_year IS NOT NULL
    """
    params = []
    if major_id:
        query = """
            SELECT DISTINCT f.study_year
            FROM feedback_forms f
            JOIN feedback_responses r ON f.id = r.form_id
            JOIN students s ON r.student_id = s.id
            JOIN users u ON s.user_id = u.id
            WHERE f.study_year IS NOT NULL AND u.major_id = %s
        """
        params = [major_id]

    query += " ORDER BY f.study_year DESC"
    rows = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return [row['study_year'] for row in rows] if rows else []
