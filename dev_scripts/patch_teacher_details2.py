import sys

old_string = """{% if current_students %}
<div class="accordion" id="studentsAccordion">
    {% for student in current_students %}
    <div class="accordion-item shadow-sm border-0 mb-2 rounded overflow-hidden">
        <h2 class="accordion-header" id="heading{{ loop.index }}">
            <button class="accordion-button collapsed py-3" type="button" data-bs-toggle="collapse" data-bs-target="#collapse{{ loop.index }}" aria-expanded="false" aria-controls="collapse{{ loop.index }}">
                <div class="d-flex justify-content-between align-items-center w-100 pe-3">
                    <span class="fw-medium text-dark">{{ student.student_name }}</span>
                    <span>
                        <span class="badge bg-success bg-opacity-10 text-success px-2 py-1 border border-success border-opacity-25 rounded-pill me-2">
                            {% if student.avg_rating == 'N/A' %}Not Submitted{% else %}{% if student.avg_rating == 'N/A' %}Not Submitted{% else %}Avg: {{ student.avg_rating }}{% endif %}{% endif %}
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
{% else %}"""

new_string = """{% if current_students %}
<div class="card shadow-sm border-0 mb-4">
    <div class="card-header bg-light d-flex justify-content-between align-items-center py-3 border-bottom-0">
        <span class="fw-bold text-navy"><i class="bi bi-people-fill text-muted me-2"></i> Enrolled Students</span>
    </div>
    <div class="card-body p-0">
        <div class="list-group list-group-flush" id="studentsAccordion">
            {% for student in current_students %}
            <div class="list-group-item p-0 border-bottom">
                <a class="d-flex justify-content-between align-items-center p-3 text-decoration-none text-body" data-bs-toggle="collapse" href="#collapse-student-{{ loop.index }}" style="cursor: pointer;">
                    <div class="d-flex align-items-center">
                        <div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center me-3 shadow-sm" style="width: 40px; height: 40px; font-size: 1.1rem; font-weight: bold; background: linear-gradient(135deg, #1C0770, #3B1B9E) !important;">
                            {{ student.student_name[:2] | upper }}
                        </div>
                        <div>
                            <h6 class="mb-0 text-navy fw-bold">{{ student.student_name }}</h6>
                            <small class="text-muted"><i class="bi bi-calendar3 me-1"></i>{{ student.submitted_at.strftime('%b %d, %Y') if student.submitted_at else '---' }}</small>
                        </div>
                    </div>
                    <div class="d-flex align-items-center">
                        {% if student.avg_rating != 'N/A' %}
                            <span class="badge bg-navy px-3 py-2 shadow-sm rounded-pill me-3" style="background: #1C0770;">
                                <i class="bi bi-star-fill text-warning me-1"></i> {{ student.avg_rating }}
                            </span>
                        {% else %}
                            <span class="badge bg-light text-muted border me-3 px-3 py-2 rounded-pill">Not Submitted</span>
                        {% endif %}
                        <i class="bi bi-chevron-down text-muted"></i>
                    </div>
                </a>
                <div class="collapse bg-light border-top" id="collapse-student-{{ loop.index }}" data-bs-parent="#studentsAccordion">
                    <div class="p-4 bg-white m-3 rounded shadow-sm border">
                        <div class="row">
                            <div class="col-md-7">
                                <h6 class="text-navy fw-bold mb-3"><i class="bi bi-ui-checks-grid me-2 text-primary"></i>Question Ratings</h6>
                                {% if student.avg_rating != 'N/A' %}
                                <div class="d-flex flex-column gap-2">
                                {% for ans in student.answers %}
                                    <div class="d-flex justify-content-between align-items-center p-2 bg-light rounded border border-light">
                                        <span class="small text-muted">{{ ans.question }}</span>
                                        <span class="badge bg-success-subtle text-success border border-success border-opacity-25 px-2">{{ ans.rating }}/5</span>
                                    </div>
                                {% endfor %}
                                </div>
                                {% else %}
                                <div class="p-3 bg-light rounded text-muted small fst-italic text-center border">
                                    Student has not submitted feedback.
                                </div>
                                {% endif %}
                            </div>
                            <div class="col-md-5">
                                <h6 class="text-navy fw-bold mb-3 mt-4 mt-md-0"><i class="bi bi-chat-right-quote me-2 text-primary"></i>Student Note</h6>
                                {% if student.comments %}
                                    <div class="p-3 bg-light rounded shadow-sm border-start border-4 border-primary fst-italic text-muted small position-relative h-100">
                                        "{{ student.comments }}"
                                    </div>
                                {% else %}
                                    <div class="p-3 bg-light rounded text-muted small opacity-75 fst-italic text-center border h-100 d-flex align-items-center justify-content-center">
                                        No additional comments provided.
                                    </div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
{% else %}"""

with open("templates/admin/feedback/teacher_details.html", "r", encoding="utf-8") as f:
    text = f.read()

if old_string not in text:
    print("WARNING: String not found. Could not patch.")
    sys.exit()

text = text.replace(old_string, new_string)
with open("templates/admin/feedback/teacher_details.html", "w", encoding="utf-8") as f:
    f.write(text)
print("Patched successfully")
