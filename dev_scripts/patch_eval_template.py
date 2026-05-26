import re

new_html = """{% extends "base.html" %}
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
        <form method="GET" class="row gx-2 gy-2 align-items-end">
            <div class="col-md-4">
                <label class="form-label small fw-medium text-navy me-2 mb-0">Subject:</label>
                <select name="subject_id" class="form-select form-select-sm" onchange="this.form.submit()">
                    {% for subj in subjects %}
                    <option value="{{ subj.subject_id }}" {% if subj.subject_id == selected_subject_id %}selected{% endif %}>
                        {{ subj.subject_name }}
                    </option>
                    {% endfor %}
                </select>
            </div>
            {% if classes %}
            <div class="col-md-4">
                <label class="form-label small fw-medium text-navy">Filter by Class:</label>
                <select name="class_id" class="form-select form-select-sm" onchange="this.form.submit()">
                    <option value="">-- All Classes --</option>
                    {% for cls in classes %}
                    <option value="{{ cls.class_id }}" {% if cls.class_id == selected_class_id %}selected{% endif %}>
                        {{ cls.class_name }}
                    </option>
                    {% endfor %}
                </select>
            </div>
            {% endif %}
        </form>
    </div>
</div>

{% if history %}
    <div class="accordion" id="historyAccordion">
    {% for year_group in history %}
        <div class="accordion-item shadow-sm border-0 mb-4">
            <h2 class="accordion-header" id="heading-{{ loop.index }}">
                <button class="accordion-button {% if not loop.first %}collapsed{% endif %} bg-navy text-white py-3 rounded" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-{{ loop.index }}" style="background: linear-gradient(135deg, #1C0770 0%, #150558 100%);">
                    <div class="d-flex justify-content-between align-items-center w-100 me-3">
                        <span class="mb-0 fw-bold"><i class="bi bi-archive-fill me-2 opacity-75"></i> Study Year: {{ year_group.study_year }}</span>
                        <span class="badge bg-light text-navy fs-6 px-3">Avg: {{ year_group.overall_avg }} | Responses: {{ year_group.total_responses }}</span>
                    </div>
                </button>
            </h2>
            <div id="collapse-{{ loop.index }}" class="accordion-collapse collapse {% if loop.first %}show{% endif %}" data-bs-parent="#historyAccordion">
                <div class="accordion-body p-0">
                    
                    {% for cls in year_group.classes %}
                    <div class="card border-0 mb-0 {% if not loop.first %}border-top{% endif %}">
                        <div class="card-header bg-light d-flex justify-content-between align-items-center py-2">
                            <span class="fw-bold text-navy"><i class="bi bi-people-fill text-muted me-2"></i> {{ cls.cohort_name }}</span>
                            <span>
                                <span class="text-muted small me-3">{{ cls.response_count }} responses</span>
                                <span class="badge bg-success-subtle text-success border border-success border-opacity-25 px-2">Cohort Avg: {{ cls.class_avg }}</span>
                            </span>
                        </div>
                        
                        <div class="card-body p-0">
                            {% if cls.students %}
                            <div class="table-responsive">
                                <table class="table table-hover align-middle mb-0 student-table">
                                    <thead class="table-light text-muted small">
                                        <tr>
                                            <th class="ps-3 w-25">Student</th>
                                            <th class="text-center" style="width: 100px;">Avg Rating</th>
                                            <th>Questions & Answers</th>
                                            <th class="w-25">Student Note</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for st in cls.students %}
                                        <tr>
                                            <td class="ps-3 fw-medium text-navy">
                                                <div class="d-flex align-items-center">
                                                    <div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center me-2" style="width: 32px; height: 32px; font-size: 0.8rem;">
                                                        {{ st.student_name[:2] | upper }}
                                                    </div>
                                                    <div>
                                                        {{ st.student_name }}
                                                        <div class="text-muted small fw-normal">{{ st.submitted_at.strftime('%b %d, %Y') if st.submitted_at else '---' }}</div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td class="text-center">
                                                {% if st.avg_rating != 'N/A' %}
                                                    <span class="badge bg-success bg-opacity-10 text-success fs-6 border border-success border-opacity-25 px-2">
                                                        <i class="bi bi-star-fill text-warning me-1"></i> {{ st.avg_rating }}
                                                    </span>
                                                {% else %}
                                                    <span class="text-muted">N/A</span>
                                                {% endif %}
                                            </td>
                                            <td>
                                                <div class="d-flex flex-column gap-1">
                                                {% for ans in st.answers %}
                                                    <div class="small">
                                                        <span class="text-muted">{{ ans.question }}:</span> 
                                                        <strong class="text-navy">{{ ans.rating }}</strong>/5
                                                    </div>
                                                {% endfor %}
                                                </div>
                                            </td>
                                            <td class="text-muted small">
                                                {% if st.comments %}
                                                    <div class="p-2 bg-light rounded fst-italic border-start border-3 border-primary">
                                                        "{{ st.comments }}"
                                                    </div>
                                                {% else %}
                                                    <span class="opacity-50">No note provided</span>
                                                {% endif %}
                                            </td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                            {% else %}
                            <div class="text-muted text-center py-3 small">
                                No detailed student responses available for this class cohort.
                            </div>
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                    
                </div>
            </div>
        </div>
    {% endfor %}
    </div>
{% else %}
<div class="alert alert-secondary border-0 shadow-sm">
    <i class="bi bi-archive me-2"></i> No historical data found for this subject/class combination.
</div>
{% endif %}

{% endblock %}
"""

with open('templates/admin/feedback/teacher_history.html', 'w', encoding='utf-8') as f:
    f.write(new_html)
print("Updated teacher_history.html")