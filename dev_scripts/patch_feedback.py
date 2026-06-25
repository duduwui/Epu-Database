import os
import re

DB_PATH = 'db.py'
ADMIN_BP_PATH = 'blueprints/admin.py'

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

# ----------------- DB.PY PATCH -----------------
db_content = read_file(DB_PATH)

# We will replace the entire feedback queries section
# Find the start: "# FEEDBACK QUERIES"
start_idx = db_content.find("# FEEDBACK QUERIES")
if start_idx != -1:
    # Find the next section: "# =========================================="
    end_idx = db_content.find("# ==========================================", start_idx + 10)
    if end_idx == -1:
        end_idx = len(db_content)
        
    new_db_code = """# FEEDBACK QUERIES

def get_latest_feedback_period(major_id=None):
    \"\"\"Finds the most recent study_year and semester to treat as 'current'\"\"\"
    query = "SELECT study_year, semester FROM feedback_forms"
    params = []
    if major_id:
        query += " WHERE created_by IN (SELECT id FROM users WHERE major_id = %s)"
        params.append(major_id)
    query += " ORDER BY study_year DESC, semester DESC LIMIT 1"
    
    row = execute_query(query, tuple(params) if params else None, fetch_one=True)
    if row:
        return {'study_year': row['study_year'], 'semester': row['semester']}
    return {'study_year': None, 'semester': None}

def get_feedback_summary(major_id=None):
    \"\"\"Get main results view: Teachers with Current Avg and All-Time Avg\"\"\"
    import json
    
    period = get_latest_feedback_period(major_id)
    curr_year = period['study_year']
    curr_sem = period['semester']
    
    query = \"\"\"
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
    \"\"\"
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
        
        if r['study_year'] == curr_year and str(r['semester']) == str(curr_sem):
            t['current_score'] += score
            t['current_count'] += count
            
    # Compute averages
    for t in teachers.values():
        t['current_avg'] = round(t['current_score'] / t['current_count'], 2) if t['current_count'] > 0 else "N/A"
        t['all_time_avg'] = round(t['all_time_score'] / t['all_time_count'], 2) if t['all_time_count'] > 0 else "N/A"
        
    return list(teachers.values())

def get_feedback_teacher_subjects(teacher_id):
    \"\"\"Get all subjects this teacher has been evaluated on\"\"\"
    query = \"\"\"
        SELECT DISTINCT s.id as subject_id, s.name as subject_name
        FROM feedback_responses r
        JOIN subjects s ON r.subject_id = s.id
        WHERE r.teacher_id = (SELECT id FROM teachers WHERE user_id = %s)
        ORDER BY s.name
    \"\"\"
    return execute_query(query, (teacher_id,), fetch_all=True) or []

def get_feedback_teacher_detail_current(teacher_id, subject_id, major_id=None):
    \"\"\"Get student details for teacher/subject specifically for the currently active period\"\"\"
    import json
    
    period = get_latest_feedback_period(major_id)
    curr_year = period.get('study_year')
    curr_sem = period.get('semester')
    
    if not curr_year or not curr_sem:
        return [], []
        
    query = \"\"\"
        SELECT 
            u.full_name as student_name, 
            r.ratings, r.comments, r.submitted_at,
            f.questions
        FROM feedback_responses r
        JOIN feedback_forms f ON r.form_id = f.id
        LEFT JOIN students st ON r.student_id = st.id
        LEFT JOIN users u ON st.user_id = u.id
        WHERE r.teacher_id = (SELECT id FROM teachers WHERE user_id = %s)
          AND r.subject_id = %s
          AND f.study_year = %s
          AND cast(f.semester as text) = cast(%s as text)
        ORDER BY r.submitted_at DESC
    \"\"\"
    rows = execute_query(query, (teacher_id, subject_id, curr_year, str(curr_sem)), fetch_all=True) or []
    
    students = []
    questions_list = []
    
    for r in rows:
        rtgs = r['ratings']
        if type(rtgs) == str:
            rtgs = json.loads(rtgs)
            
        if not questions_list and r['questions']:
            q_data = r['questions']
            if type(q_data) == str:
                q_data = json.loads(q_data)
            if isinstance(q_data, list):
                questions_list = [q.get('text', str(q)) if isinstance(q, dict) else str(q) for q in q_data]
                
        student_score = 0
        student_count = 0
        answers = []
        
        if rtgs:
            if isinstance(rtgs, dict):
                for idx_str, v in rtgs.items():
                    if str(v).isdigit():
                        answers.append({'index': int(idx_str), 'value': int(v)})
                        student_score += int(v)
                        student_count += 1
            elif isinstance(rtgs, list):
                for idx, v in enumerate(rtgs):
                    if str(v).isdigit():
                        answers.append({'index': idx, 'value': int(v)})
                        student_score += int(v)
                        student_count += 1
                        
        avg_rating = round(student_score / student_count, 2) if student_count > 0 else "N/A"
        
        display_answers = []
        if questions_list:
            for idx, q_text in enumerate(questions_list):
                val = next((item['value'] for item in answers if item['index'] == idx), 'N/A')
                display_answers.append({'question': q_text, 'rating': val})
        else:
            for pr in answers:
                display_answers.append({'question': f"Question {pr['index'] + 1}", 'rating': pr['value']})
                
        students.append({
            'student_name': r['student_name'] or 'Anonymous',
            'submitted_at': r['submitted_at'],
            'avg_rating': avg_rating,
            'comments': r['comments'] or '',
            'answers': display_answers
        })
        
    return students, questions_list

def get_feedback_teacher_history_by_year(teacher_id, subject_id):
    \"\"\"Get historical records grouped cleanly strictly by Study Year and Class\"\"\"
    import json
    query = \"\"\"
        SELECT 
            f.study_year,
            c.name as class_name, c.semester as class_semester,
            COUNT(r.id) as response_count,
            jsonb_agg(r.ratings) as all_ratings
        FROM feedback_responses r
        JOIN feedback_forms f ON r.form_id = f.id
        LEFT JOIN classes c ON r.snapshot_class_id = c.id
        WHERE r.teacher_id = (SELECT id FROM teachers WHERE user_id = %s)
          AND r.subject_id = %s
        GROUP BY f.study_year, c.name, c.semester
        ORDER BY f.study_year DESC, c.semester DESC
    \"\"\"
    rows = execute_query(query, (teacher_id, subject_id), fetch_all=True) or []
    
    history = {}
    for r in rows:
        sy = r['study_year'] or 'Unknown Year'
        if sy not in history:
            history[sy] = {
                'study_year': sy,
                'total_responses': 0,
                'classes': [],
                'total_score': 0,
                'total_ratings': 0
            }
            
        grp = history[sy]
        grp['total_responses'] += r['response_count']
        
        class_score = 0
        class_rating_cnt = 0
        
        all_rat = r.pop('all_ratings')
        if all_rat:
            for rtgs in all_rat:
                if type(rtgs) == str:
                    rtgs = json.loads(rtgs)
                if rtgs and isinstance(rtgs, dict):
                    for v in rtgs.values():
                        if str(v).isdigit():
                            class_score += int(v)
                            class_rating_cnt += 1
                elif rtgs and isinstance(rtgs, list):
                    for v in rtgs:
                        if str(v).isdigit():
                            class_score += int(v)
                            class_rating_cnt += 1
                            
        grp['total_score'] += class_score
        grp['total_ratings'] += class_rating_cnt
        
        class_avg = round(class_score / class_rating_cnt, 2) if class_rating_cnt > 0 else "N/A"
        
        grp['classes'].append({
            'cohort_name': f"{r['class_name'] or 'Unknown Class'} (Sem {r['class_semester'] or '?'})",
            'response_count': r['response_count'],
            'class_avg': class_avg
        })
        
    for grp in history.values():
        grp['overall_avg'] = round(grp['total_score'] / grp['total_ratings'], 2) if grp['total_ratings'] > 0 else "N/A"
        
    return list(history.values())

def get_feedback_analytics_flat(major_id=None):
    \"\"\"Raw analytics output bridging answers into table columns\"\"\"
    import json
    query = \"\"\"
        SELECT 
            u_teacher.full_name as teacher_name,
            s.name as subject_name,
            u_student.full_name as student_name,
            f.study_year,
            r.ratings, r.comments,
            f.questions
        FROM feedback_responses r
        JOIN teachers t ON r.teacher_id = t.id
        JOIN users u_teacher ON t.user_id = u_teacher.id
        JOIN subjects s ON r.subject_id = s.id
        JOIN feedback_forms f ON r.form_id = f.id
        LEFT JOIN students st ON r.student_id = st.id
        LEFT JOIN users u_student ON st.user_id = u_student.id
    \"\"\"
    params = []
    if major_id:
        query += " WHERE u_teacher.major_id = %s "
        params.append(major_id)
        
    query += " ORDER BY teacher_name, subject_name, student_name"
    rows = execute_query(query, tuple(params) if params else None, fetch_all=True) or []
    
    max_questions = 0
    results = []
    
    for r in rows:
        rtgs = r['ratings']
        if type(rtgs) == str:
             rtgs = json.loads(rtgs)
             
        answers = []
        if isinstance(rtgs, dict):
            for idx_str, v in rtgs.items():
                if str(v).isdigit():
                    answers.append({'i': int(idx_str), 'v': int(v)})
        elif isinstance(rtgs, list):
            for idx, v in enumerate(rtgs):
                if str(v).isdigit():
                    answers.append({'i': idx, 'v': int(v)})
                    
        # find max index to ensure we have headers
        for a in answers:
            if a['i'] >= max_questions:
                max_questions = a['i'] + 1
        
        ans_dict = {f"q{a['i'] + 1}": a['v'] for a in answers}
        
        row_data = {
            'teacher': r['teacher_name'],
            'subject': r['subject_name'],
            'student': r['student_name'] or 'Anonymous',
            'study_year': r['study_year'],
            'notes': r['comments'] or '',
        }
        row_data.update(ans_dict)
        results.append(row_data)
        
    return results, max_questions

"""
    
    new_db = db_content[:start_idx] + new_db_code + "\n\n" + db_content[end_idx:]
    write_file(DB_PATH, new_db)
    print("Patched db.py successfully.")

# ----------------- ADMIN.PY PATCH -----------------
admin_content = read_file(ADMIN_BP_PATH)

# Replace feedback_results
feedback_results_idx = admin_content.find("def feedback_results():")
if feedback_results_idx != -1:
    route_end = admin_content.find("@admin_bp.route", feedback_results_idx)
    if route_end == -1: route_end = len(admin_content)
    
    new_results_func = """def feedback_results():
    from flask import session, render_template
    import db
    
    user_id = session.get('user_id')
    user = db.get_user_by_id(user_id)
    major_id = user.get('major_id') if user else None
    
    summary = db.get_feedback_summary(major_id)
    return render_template("admin/feedback/results.html", summary=summary)

"""
    start_route = admin_content.rfind("@admin_bp.route", 0, feedback_results_idx)
    admin_content = admin_content[:start_route] + "@admin_bp.route('/admin/feedback/results', methods=['GET'])\n@admin_required\n" + new_results_func + admin_content[route_end:]

# Replace teacher details
admin_content = read_file(ADMIN_BP_PATH) # reload to get indices right
teacher_details_idx = admin_content.find("def feedback_teacher_details(teacher_id):")
if teacher_details_idx != -1:
    route_end = admin_content.find("@admin_bp.route", teacher_details_idx)
    if route_end == -1: route_end = len(admin_content)
    
    new_td_func = """def feedback_teacher_details(teacher_id):
    from flask import request, flash, redirect, render_template, session
    import db
    
    user_id = session.get('user_id')
    user = db.get_user_by_id(user_id)
    major_id = user.get('major_id') if user else None

    teacher = db.execute_query("SELECT full_name FROM users WHERE id = %s", (teacher_id,), fetch_one=True)
    if not teacher:
        flash("Teacher not found", "danger")
        return redirect('/admin/feedback/results')
        
    subjects = db.get_feedback_teacher_subjects(teacher_id)
    
    selected_subject_id = request.args.get('subject_id', type=int)
    if not selected_subject_id and subjects:
        selected_subject_id = subjects[0]['subject_id']
        
    current_students = []
    questions_list = []
    if selected_subject_id:
        current_students, questions_list = db.get_feedback_teacher_detail_current(teacher_id, selected_subject_id, major_id)

    return render_template("admin/feedback/teacher_details.html",
                           teacher_name=teacher['full_name'],
                           teacher_id=teacher_id,
                           subjects=subjects,
                           selected_subject_id=selected_subject_id,
                           current_students=current_students,
                           questions_list=questions_list)

@admin_bp.route('/admin/feedback/teacher/<int:teacher_id>/history', methods=['GET'])
@admin_required
def feedback_teacher_history(teacher_id):
    from flask import request, flash, redirect, render_template
    import db
    
    teacher = db.execute_query("SELECT full_name FROM users WHERE id = %s", (teacher_id,), fetch_one=True)
    if not teacher:
        flash("Teacher not found", "danger")
        return redirect('/admin/feedback/results')
        
    subjects = db.get_feedback_teacher_subjects(teacher_id)
    selected_subject_id = request.args.get('subject_id', type=int)
    if not selected_subject_id and subjects:
        selected_subject_id = subjects[0]['subject_id']
        
    history = []
    if selected_subject_id:
        history = db.get_feedback_teacher_history_by_year(teacher_id, selected_subject_id)
        
    return render_template("admin/feedback/teacher_history.html",
                           teacher_name=teacher['full_name'],
                           teacher_id=teacher_id,
                           subjects=subjects,
                           selected_subject_id=selected_subject_id,
                           history=history)

@admin_bp.route('/admin/feedback/analytics', methods=['GET'])
@admin_required
def feedback_analytics():
    from flask import session, render_template
    import db
    
    user_id = session.get('user_id')
    user = db.get_user_by_id(user_id)
    major_id = user.get('major_id') if user else None
    
    analytics_data, max_q = db.get_feedback_analytics_flat(major_id)
    return render_template("admin/feedback/analytics.html", analytics_data=analytics_data, max_q=max_q)

"""
    start_route = admin_content.rfind("@admin_bp.route", 0, teacher_details_idx)
    admin_content = admin_content[:start_route] + "@admin_bp.route('/admin/feedback/teacher/<int:teacher_id>', methods=['GET'])\n@admin_required\n" + new_td_func + admin_content[route_end:]
    write_file(ADMIN_BP_PATH, admin_content)
    print("Patched blueprints/admin.py successfully.")

# ----------------- CREATE TEMPLATES -----------------

os.makedirs('templates/admin/feedback', exist_ok=True)

# 1. results.html
results_html = """{% extends "base.html" %}
{% block title %}Feedback Results{% endblock %}

{% block content %}
<div class="row align-items-center mb-3">
    <div class="col-md-6">
        <h2 class="h4 text-navy fw-bold mb-0">Feedback Results</h2>
        <p class="text-muted small mb-0">Overview of all teachers</p>
    </div>
    <div class="col-md-6 text-end">
        <a href="/admin/feedback/analytics" class="btn btn-sm btn-primary">
            <i class="bi bi-graph-up"></i> Analytics / Get Insights
        </a>
    </div>
</div>

<div class="card shadow-sm border-0">
    <div class="card-body p-0">
        <div class="table-responsive">
            <table class="table table-hover align-middle mb-0">
                <thead class="table-light text-navy">
                    <tr>
                        <th class="ps-4">Teacher Name</th>
                        <th class="text-center">Current Active Semester Average</th>
                        <th class="text-center">Historical All-Time Average</th>
                        <th class="text-center pe-4">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for row in summary %}
                    <tr>
                        <td class="ps-4 fw-medium">{{ row.teacher_name }}</td>
                        <td class="text-center">
                            {% if row.current_avg != "N/A" %}
                                <span class="badge bg-success bg-opacity-10 text-success fs-6 border border-success border-opacity-25 px-3">
                                    <i class="bi bi-star-fill text-warning me-1"></i> {{ row.current_avg }}
                                </span>
                            {% else %}
                                <span class="text-muted small">No Data</span>
                            {% endif %}
                        </td>
                        <td class="text-center">
                            {% if row.all_time_avg != "N/A" %}
                                <span class="badge bg-secondary bg-opacity-10 text-secondary fs-6 border border-secondary border-opacity-25 px-3">
                                    {{ row.all_time_avg }}
                                </span>
                            {% else %}
                                <span class="text-muted small">No Data</span>
                            {% endif %}
                        </td>
                        <td class="text-center pe-4">
                            <a href="/admin/feedback/teacher/{{ row.teacher_id }}" class="btn btn-sm btn-outline-primary shadow-sm" data-bs-toggle="tooltip" title="View Student Feedback Details">
                                Details <i class="bi bi-arrow-right-short"></i>
                            </a>
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="4" class="text-center text-muted py-4">No feedback records found.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
"""
write_file('templates/admin/feedback/results.html', results_html)

# 2. teacher_details.html
td_html = """{% extends "base.html" %}
{% block title %}Teacher Feedback Details{% endblock %}

{% block content %}
<div class="mb-3">
    <a href="/admin/feedback/results" class="text-decoration-none text-muted">
        <i class="bi bi-arrow-left"></i> Back to Results
    </a>
</div>

<div class="row align-items-center mb-3">
    <div class="col-md-6">
        <h2 class="h4 text-navy fw-bold mb-0">{{ teacher_name }}</h2>
        <p class="text-muted small mb-0">Current Semester Focus View</p>
    </div>
    <div class="col-md-6 text-end">
        <a href="/admin/feedback/teacher/{{ teacher_id }}/history{% if selected_subject_id %}?subject_id={{ selected_subject_id }}{% endif %}" class="btn btn-sm btn-outline-secondary">
            <i class="bi bi-clock-history"></i> Previous Years History
        </a>
    </div>
</div>

<div class="card shadow-sm border-0 mb-4">
    <div class="card-body bg-light">
        <form method="GET" class="row gx-2 gy-2 align-items-end">
            <div class="col-md-4">
                <label class="form-label small fw-medium text-navy">Filter by Subject</label>
                <select name="subject_id" class="form-select form-select-sm" onchange="this.form.submit()">
                    {% for subj in subjects %}
                    <option value="{{ subj.subject_id }}" {% if subj.subject_id == selected_subject_id %}selected{% endif %}>
                        {{ subj.subject_name }}
                    </option>
                    {% endfor %}
                </select>
            </div>
        </form>
    </div>
</div>

<h5 class="h6 text-navy fw-bold mb-3">Current Semester Active Feedback</h5>

{% if current_students %}
<div class="accordion" id="studentsAccordion">
    {% for student in current_students %}
    <div class="accordion-item shadow-sm border-0 mb-2 rounded overflow-hidden">
        <h2 class="accordion-header" id="heading{{ loop.index }}">
            <button class="accordion-button collapsed py-3" type="button" data-bs-toggle="collapse" data-bs-target="#collapse{{ loop.index }}" aria-expanded="false" aria-controls="collapse{{ loop.index }}">
                <div class="d-flex justify-content-between align-items-center w-100 pe-3">
                    <span class="fw-medium text-dark">{{ student.student_name }}</span>
                    <span>
                        <span class="badge bg-success bg-opacity-10 text-success px-2 py-1 border border-success border-opacity-25 rounded-pill me-2">
                            Avg: {{ student.avg_rating }}
                        </span>
                        <small class="text-muted" style="font-size: 0.75rem;">{{ student.submitted_at.strftime('%Y-%m-%d') if student.submitted_at else '' }}</small>
                    </span>
                </div>
            </button>
        </h2>
        <div id="collapse{{ loop.index }}" class="accordion-collapse collapse" aria-labelledby="heading{{ loop.index }}" data-bs-parent="#studentsAccordion">
            <div class="accordion-body bg-light border-top">
                
                <h6 class="text-navy fw-bold small text-uppercase mb-2">Question Breakdown</h6>
                <div class="table-responsive mb-3">
                    <table class="table table-sm table-bordered bg-white rounded shadow-sm m-0">
                        <thead class="table-light">
                            <tr>
                                <th>Question</th>
                                <th class="text-center" width="100">Rating</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for ans in student.answers %}
                            <tr>
                                <td class="text-muted">{{ ans.question }}</td>
                                <td class="text-center fw-medium text-dark">{{ ans.rating }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>

                {% if student.comments %}
                <h6 class="text-navy fw-bold small text-uppercase mb-2 mt-3">Student Note</h6>
                <div class="p-3 bg-white border rounded text-dark fst-italic shadow-sm">
                    "{{ student.comments }}"
                </div>
                {% endif %}

            </div>
        </div>
    </div>
    {% endfor %}
</div>
{% else %}
<div class="alert alert-info border-0 shadow-sm">
    <i class="bi bi-info-circle me-2"></i> No active feedback submitted by students for this subject currently.
</div>
{% endif %}

{% endblock %}
"""
write_file('templates/admin/feedback/teacher_details.html', td_html)

# 3. teacher_history.html
history_html = """{% extends "base.html" %}
{% block title %}Feedback History{% endblock %}

{% block content %}
<div class="mb-3">
    <a href="/admin/feedback/teacher/{{ teacher_id }}{% if selected_subject_id %}?subject_id={{ selected_subject_id }}{% endif %}" class="text-decoration-none text-muted">
        <i class="bi bi-arrow-left"></i> Back to Current Semester View
    </a>
</div>

<div class="row align-items-center mb-4">
    <div class="col-md-8">
        <h2 class="h4 text-navy fw-bold mb-0">Historical Feedback Archives</h2>
        <p class="text-muted small mb-0">{{ teacher_name }} | Subject History Silos</p>
    </div>
</div>

<div class="card shadow-sm border-0 mb-4">
    <div class="card-body bg-light py-2">
        <form method="GET" class="d-flex align-items-center">
            <label class="form-label small fw-medium text-navy me-2 mb-0">Subject:</label>
            <select name="subject_id" class="form-select form-select-sm w-auto" onchange="this.form.submit()">
                {% for subj in subjects %}
                <option value="{{ subj.subject_id }}" {% if subj.subject_id == selected_subject_id %}selected{% endif %}>
                    {{ subj.subject_name }}
                </option>
                {% endfor %}
            </select>
        </form>
    </div>
</div>

{% if history %}
    {% for year_group in history %}
    <div class="card border-0 shadow-sm mb-4">
        <div class="card-header bg-navy text-white d-flex justify-content-between align-items-center py-3" style="background: linear-gradient(135deg, #1C0770 0%, #150558 100%);">
            <h5 class="mb-0 fw-bold"><i class="bi bi-archive-fill me-2 opacity-75"></i> Study Year: {{ year_group.study_year }}</h5>
            <span class="badge bg-light text-navy fs-6 px-3">Avg: {{ year_group.overall_avg }}</span>
        </div>
        <div class="card-body p-0">
            <table class="table table-hover align-middle mb-0">
                <thead class="table-light">
                    <tr>
                        <th class="ps-4">Origin Cohort (Class)</th>
                        <th class="text-center">Total Responses</th>
                        <th class="text-center pe-4">Cohort Average</th>
                    </tr>
                </thead>
                <tbody>
                    {% for cls in year_group.classes %}
                    <tr>
                        <td class="ps-4 fw-medium text-dark"><i class="bi bi-people-fill text-muted me-2"></i> {{ cls.cohort_name }}</td>
                        <td class="text-center text-muted">{{ cls.response_count }} students</td>
                        <td class="text-center pe-4 fw-bold text-navy">{{ cls.class_avg }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    {% endfor %}
{% else %}
<div class="alert alert-secondary border-0 shadow-sm">
    <i class="bi bi-archive me-2"></i> No historical data found for this subject.
</div>
{% endif %}

{% endblock %}
"""
write_file('templates/admin/feedback/teacher_history.html', history_html)

# 4. analytics.html
analytics_html = """{% extends "base.html" %}
{% block title %}Feedback Analytics Insights{% endblock %}

{% block content %}
<div class="mb-3">
    <a href="/admin/feedback/results" class="text-decoration-none text-muted">
        <i class="bi bi-arrow-left"></i> Back to Feedback Results
    </a>
</div>

<h2 class="h4 text-navy fw-bold mb-3">Global Feedback Analytics <i class="bi bi-bar-chart-fill ms-2 text-primary opacity-50"></i></h2>
<p class="text-muted small">Flat data view for deep dive sorting and student note analysis across all teachers and studying periods.</p>

<div class="card shadow-sm border-0">
    <div class="card-body p-0">
        <div class="table-responsive" style="max-height: 70vh;">
            <table class="table table-hover table-bordered align-middle mb-0 text-nowrap" id="analyticsTable">
                <thead class="table-light text-navy position-sticky top-0 shadow-sm" style="z-index: 10;">
                    <tr>
                        <th role="button" onclick="sortTable(0)">Teacher <i class="bi bi-arrow-down-up small opacity-50 ms-1"></i></th>
                        <th role="button" onclick="sortTable(1)">Subject <i class="bi bi-arrow-down-up small opacity-50 ms-1"></i></th>
                        <th role="button" onclick="sortTable(2)">Student <i class="bi bi-arrow-down-up small opacity-50 ms-1"></i></th>
                        <th role="button" onclick="sortTable(3)">Study Year <i class="bi bi-arrow-down-up small opacity-50 ms-1"></i></th>
                        {% for i in range(max_q) %}
                        <th class="text-center" role="button" onclick="sortTable({{ 4 + i }})">Q{{ i + 1 }} <i class="bi bi-arrow-down-up small opacity-50 ms-1"></i></th>
                        {% endfor %}
                        <th>Student Note</th>
                    </tr>
                </thead>
                <tbody>
                    {% for row in analytics_data %}
                    <tr>
                        <td class="fw-medium">{{ row.teacher }}</td>
                        <td class="text-muted">{{ row.subject }}</td>
                        <td>{{ row.student }}</td>
                        <td>{{ row.study_year }}</td>
                        {% for i in range(max_q) %}
                        <td class="text-center fw-bold text-navy">{{ row['q' ~ (i+1)] if row['q' ~ (i+1)] is defined else '-' }}</td>
                        {% endfor %}
                        <td class="text-wrap" style="min-width: 250px; max-width: 400px;">
                            {% if row.notes %}
                                <span class="fst-italic text-muted">"{{ row.notes }}"</span>
                            {% else %}
                                <span class="text-muted opacity-50">-</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="100%" class="text-center py-4">No analytics data available.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>

<script>
// Simple client side sorter for the analytics table
function sortTable(n) {
  var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
  table = document.getElementById("analyticsTable");
  switching = true;
  dir = "asc"; 
  while (switching) {
    switching = false;
    rows = table.rows;
    for (i = 1; i < (rows.length - 1); i++) {
        shouldSwitch = false;
        x = rows[i].getElementsByTagName("TD")[n];
        y = rows[i + 1].getElementsByTagName("TD")[n];
        
        let xVal = x.innerHTML.toLowerCase().replace(/<[^>]*>?/gm, '');
        let yVal = y.innerHTML.toLowerCase().replace(/<[^>]*>?/gm, '');
        
        if (!isNaN(parseFloat(xVal)) && !isNaN(parseFloat(yVal))) {
            xVal = parseFloat(xVal);
            yVal = parseFloat(yVal);
        }

        if (dir == "asc") {
            if (xVal > yVal) { shouldSwitch = true; break; }
        } else if (dir == "desc") {
            if (xVal < yVal) { shouldSwitch = true; break; }
        }
    }
    if (shouldSwitch) {
        rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
        switching = true;
        switchcount ++;
    } else {
        if (switchcount == 0 && dir == "asc") {
            dir = "desc";
            switching = true;
        }
    }
  }
}
</script>
{% endblock %}
"""
write_file('templates/admin/feedback/analytics.html', analytics_html)
print("Created all HTML templates successfully.")
