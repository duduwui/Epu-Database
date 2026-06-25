import re

with open('templates/admin/feedback/teacher_history.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace table-responsive block with collapsible accordion list group
old_table_pattern = re.compile(r'<div class="table-responsive">.*?</table>\s*</div>', re.DOTALL)

new_ui = """<div class="list-group list-group-flush">
    {% for st in cls.students %}
    <div class="list-group-item p-0 border-bottom">
        <a class="d-flex justify-content-between align-items-center p-3 text-decoration-none text-body" data-bs-toggle="collapse" href="#collapse-student-{{ cls.class_id }}-{{ loop.index }}" style="cursor: pointer;">
            <div class="d-flex align-items-center">
                <div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center me-3 shadow-sm" style="width: 40px; height: 40px; font-size: 1.1rem; font-weight: bold; background: linear-gradient(135deg, #1C0770, #3B1B9E) !important;">
                    {{ st.student_name[:2] | upper }}
                </div>
                <div>
                    <h6 class="mb-0 text-navy fw-bold">{{ st.student_name }}</h6>
                    <small class="text-muted"><i class="bi bi-calendar3 me-1"></i>{{ st.submitted_at.strftime('%b %d, %Y') if st.submitted_at else '---' }}</small>
                </div>
            </div>
            <div class="d-flex align-items-center">
                {% if st.avg_rating != 'N/A' %}
                    <span class="badge bg-navy px-3 py-2 shadow-sm rounded-pill me-3" style="background: #1C0770;">
                         <i class="bi bi-star-fill text-warning me-1"></i> {{ st.avg_rating }}
                    </span>
                {% else %}
                    <span class="badge bg-light text-muted border me-3 px-3 py-2 rounded-pill">N/A</span>
                {% endif %}
                <i class="bi bi-chevron-down text-muted"></i>
            </div>
        </a>
        <div class="collapse bg-light border-top" id="collapse-student-{{ cls.class_id }}-{{ loop.index }}">
            <div class="p-4 bg-white m-3 rounded shadow-sm border">
                <div class="row">
                    <div class="col-md-7">
                        <h6 class="text-navy fw-bold mb-3"><i class="bi bi-ui-checks-grid me-2 text-primary"></i>Question Ratings</h6>
                        <div class="d-flex flex-column gap-2">
                        {% for ans in st.answers %}
                            <div class="d-flex justify-content-between align-items-center p-2 bg-light rounded border border-light">
                                <span class="small text-muted">{{ ans.question }}</span>
                                <span class="badge bg-success-subtle text-success border border-success border-opacity-25 px-2">{{ ans.rating }}/5</span>
                            </div>
                        {% endfor %}
                        </div>
                    </div>
                    <div class="col-md-5">
                        <h6 class="text-navy fw-bold mb-3 mt-4 mt-md-0"><i class="bi bi-chat-right-quote me-2 text-primary"></i>Student Note</h6>
                        {% if st.comments %}
                            <div class="p-3 bg-light rounded shadow-sm border-start border-4 border-primary fst-italic text-muted small position-relative h-100">
                                "{{ st.comments }}"
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
"""

content = old_table_pattern.sub(new_ui, content)

with open('templates/admin/feedback/teacher_history.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Finished UI patch")
