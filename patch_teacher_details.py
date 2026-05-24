new_html = """{% extends 'base.html' %}
{% block title %}Feedback Details: {{ teacher_name }}{% endblock %}

{% block content %}
<div class="container-fluid py-4">
    <!-- Header -->
    <div class="row align-items-center mb-4">
        <div class="col-md-8">
            <h3 class="mb-1 fw-bold text-navy">
                <i class="bi bi-person-lines-fill me-2 text-primary"></i> 
                {{ teacher_name }}
            </h3>
            <p class="text-muted mb-0 fs-6">Comprehensive Feedback Report</p>
        </div>
        <div class="col-md-4 text-md-end mt-3 mt-md-0 d-flex justify-content-md-end gap-2">
            <a href="{{ url_for('admin.feedback_results') }}" class="btn btn-outline-secondary btn-sm">
                <i class="bi bi-arrow-left me-1"></i> Back to Results
            </a>
        </div>
    </div>

    <!-- Filters Card -->
    <div class="card border-0 shadow-sm mb-4">
        <div class="card-body bg-light rounded">
            <form method="GET" action="{{ url_for('admin.feedback_teacher_details', teacher_id=teacher_id) }}" class="row g-3 align-items-end">
                <div class="col-md-5">
                    <label class="form-label mb-1 text-muted small fw-bold">Select Subject</label>
                    <select name="subject_id" class="form-select form-select-sm" onchange="this.form.submit()">
                        {% if not subjects %}
                            <option value="">No subjects found</option>
                        {% endif %}
                        {% for subj in subjects %}
                        <option value="{{ subj.subject_id }}" {% if selected_subject_id == subj.subject_id %}selected{% endif %}>
                            {{ subj.subject_name }}
                        </option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-5">
                    <label class="form-label mb-1 text-muted small fw-bold">Study Year</label>
                    <select name="study_year" class="form-select form-select-sm" onchange="this.form.submit()">
                        {% if not history %}
                            <option value="">No history available</option>
                        {% endif %}
                        {% for h in history %}
                        <option value="{{ h.study_year }}" {% if selected_year == h.study_year %}selected{% endif %}>
                            {{ h.study_year }}
                        </option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-2">
                    <button type="submit" class="btn btn-primary btn-sm w-100"><i class="bi bi-arrow-repeat me-1"></i>Load</button>
                    <input type="hidden" name="teacher_id" value="{{ teacher_id }}">
                </div>
            </form>
        </div>
    </div>

    {% if not current_details and not history %}
    <div class="card shadow-sm border-0">
        <div class="card-body py-5 text-center text-muted">
            <i class="bi bi-inbox fs-1 d-block mb-3 text-secondary opacity-50"></i>
            <h5 class="fw-normal">No detailed feedback data available for this selection.</h5>
        </div>
    </div>
    {% else %}
    
    <!-- Tab Navigation -->
    <ul class="nav nav-tabs border-bottom-0 mb-4" id="feedbackTabs" role="tablist">
        <li class="nav-item" role="presentation">
            <button class="nav-link active fw-bold text-navy px-4 shadow-sm rounded-top" id="trend-tab" data-bs-toggle="tab" data-bs-target="#trend" type="button" role="tab" aria-controls="trend" aria-selected="true">
                <i class="bi bi-clock-history me-2"></i>Trend History
            </button>
        </li>
        <li class="nav-item" role="presentation">
            <button class="nav-link fw-bold text-navy px-4 shadow-sm rounded-top ms-2" id="quant-tab" data-bs-toggle="tab" data-bs-target="#quant" type="button" role="tab" aria-controls="quant" aria-selected="false">
                <i class="bi bi-bar-chart-fill me-2"></i>Quantitative
            </button>
        </li>
        <li class="nav-item" role="presentation">
            <button class="nav-link fw-bold text-navy px-4 shadow-sm rounded-top ms-2" id="qual-tab" data-bs-toggle="tab" data-bs-target="#qual" type="button" role="tab" aria-controls="qual" aria-selected="false">
                <i class="bi bi-chat-square-quote-fill me-2"></i>Qualitative Comments
            </button>
        </li>
    </ul>

    <!-- Tab Content -->
    <div class="tab-content" id="feedbackTabsContent">
        
        <!-- Tab 1: Trend History -->
        <div class="tab-pane fade show active" id="trend" role="tabpanel" aria-labelledby="trend-tab">
            <div class="card border-0 shadow-sm">
                <div class="card-header bg-white border-bottom py-3">
                    <h5 class="mb-0 fw-bold text-navy">Performance Over Time (All Classes)</h5>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover align-middle mb-0">
                            <thead class="bg-light">
                                <tr>
                                    <th class="px-4 py-3">Study Year</th>
                                    <th>Total Responses</th>
                                    <th>Overall Avg Rating</th>
                                    <th>Class Breakdown</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for h in history %}
                                <tr>
                                    <td class="px-4 py-3 fw-bold">{{ h.study_year }}</td>
                                    <td><span class="badge bg-secondary rounded-pill">{{ h.total_responses }}</span></td>
                                    <td>
                                        <h5 class="mb-0 {% if h.overall_avg != 'N/A' and h.overall_avg >= 4.0 %}text-success{% elif h.overall_avg != 'N/A' and h.overall_avg >= 2.5 %}text-primary{% else %}text-danger{% endif %} fw-bold">
                                            {{ h.overall_avg }} <small class="fw-normal text-muted fs-6">/ 5.0</small>
                                        </h5>
                                    </td>
                                    <td>
                                        <ul class="list-unstyled mb-0 small">
                                            {% for cls in h.classes %}
                                            <li class="mb-1 text-muted">
                                                <i class="bi bi-dot"></i> {{ cls.class_name }}: 
                                                <strong>{{ cls.class_avg }}</strong> ({{ cls.response_count }} resp)
                                            </li>
                                            {% endfor %}
                                        </ul>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tab 2: Quantitative Data -->
        <div class="tab-pane fade" id="quant" role="tabpanel" aria-labelledby="quant-tab">
            {% if not current_details %}
                <div class="alert alert-info border-0 shadow-sm"><i class="bi bi-info-circle me-2"></i> No detailed responses recorded in {{ selected_year }}.</div>
            {% else %}
                {% for cls in current_details %}
                <div class="card border-0 shadow-sm mb-4">
                    <div class="card-header bg-white border-bottom py-3 d-flex justify-content-between align-items-center">
                        <div>
                            <h5 class="mb-0 fw-bold text-navy"><i class="bi bi-people-fill me-2 text-primary"></i>Class: {{ cls.class_name }}</h5>
                            <small class="text-muted">Total Responses: {{ cls.response_count }}</small>
                        </div>
                        <div class="text-end">
                            <span class="badge {% if cls.class_avg != 'N/A' and cls.class_avg >= 4.0 %}bg-success{% elif cls.class_avg != 'N/A' and cls.class_avg >= 2.5 %}bg-primary{% else %}bg-danger{% endif %} fs-6 px-3 py-2 rounded-pill shadow-sm">
                                Class Average: {{ cls.class_avg }} / 5.0
                            </span>
                        </div>
                    </div>
                    <div class="card-body bg-light">
                        <h6 class="fw-bold mb-3">Breakdown by Question</h6>
                        {% if questions_list %}
                            {% for q_text in questions_list %}
                                {% set q_idx = loop.index0 %}
                                {% set q_avg = cls.per_question_avg.get(q_idx, 'N/A') %}
                                {% set pct = (q_avg / 5.0 * 100) if q_avg != 'N/A' else 0 %}
                                <div class="mb-3">
                                    <div class="d-flex justify-content-between mb-1">
                                        <span class="small fw-semibold text-secondary">{{ loop.index }}. {{ q_text }}</span>
                                        <span class="small fw-bold {% if q_avg != 'N/A' and q_avg >= 4.0 %}text-success{% elif q_avg != 'N/A' and q_avg >= 2.5 %}text-primary{% else %}text-danger{% endif %}">{{ q_avg }}</span>
                                    </div>
                                    <div class="progress" style="height: 8px;">
                                        <div class="progress-bar {% if q_avg != 'N/A' and q_avg >= 4.0 %}bg-success{% elif q_avg != 'N/A' and q_avg >= 2.5 %}bg-primary{% else %}bg-danger{% endif %}" role="progressbar" style="width: {{ pct }}%;" aria-valuenow="{{ pct }}" aria-valuemin="0" aria-valuemax="100"></div>
                                    </div>
                                </div>
                            {% endfor %}
                        {% else %}
                            <p class="text-muted small italic">No question texts available.</p>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            {% endif %}
        </div>

        <!-- Tab 3: Qualitative Comments -->
        <div class="tab-pane fade" id="qual" role="tabpanel" aria-labelledby="qual-tab">
            {% if not current_details %}
                <div class="alert alert-info border-0 shadow-sm"><i class="bi bi-info-circle me-2"></i> No comments recorded in {{ selected_year }}.</div>
            {% else %}
                <div class="row row-cols-1 row-cols-lg-2 g-4">
                {% for cls in current_details %}
                    <div class="col">
                        <div class="card h-100 border-0 shadow-sm mb-4">
                            <div class="card-header bg-white border-bottom py-3">
                                <h6 class="mb-0 fw-bold text-navy"><i class="bi bi-chat-right-text-fill me-2 text-primary"></i>Comments: {{ cls.class_name }}</h6>
                            </div>
                            <div class="card-body p-0" style="max-height: 400px; overflow-y: auto;">
                                <ul class="list-group list-group-flush">
                                {% set has_comments = false %}
                                {% for r in cls.students %}
                                    {% if r.comments and r.comments.strip() != '' %}
                                        {% set has_comments = true %}
                                        <li class="list-group-item p-4">
                                            <div class="d-flex w-100 justify-content-between mb-2">
                                                <small class="text-muted"><i class="bi bi-person-circle me-1"></i> Anonymous</small>
                                                <small class="badge bg-light text-dark border">
                                                    Avg: <strong class="{% if r.overall_avg != 'N/A' and r.overall_avg >= 4 %}text-success{% elif r.overall_avg != 'N/A' and r.overall_avg >= 2.5 %}text-primary{% else %}text-danger{% endif %}">{{ r.overall_avg }}</strong>
                                                </small>
                                            </div>
                                            <p class="mb-1 text-dark fs-6" style="white-space: pre-wrap;">"{{ r.comments }}"</p>
                                        </li>
                                    {% endif %}
                                {% endfor %}
                                {% if not has_comments %}
                                    <li class="list-group-item p-4 text-center text-muted small"><i class="bi bi-chat-left-quote fs-3 d-block mb-2 opacity-25"></i>No text comments provided by students in this class.</li>
                                {% endif %}
                                </ul>
                            </div>
                        </div>
                    </div>
                {% endfor %}
                </div>
            {% endif %}
        </div>

    </div>
    {% endif %}
</div>
{% endblock %}
"""

with open('templates/admin/feedback/teacher_details.html', 'w', encoding='utf-8') as f:
    f.write(new_html)
print("SUCCESS!")