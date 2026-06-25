new_html = """{% extends 'base.html' %}
{% block title %}Feedback Results{% endblock %}
{% block content %}
<div class="container-fluid py-4">
    <div class="row align-items-center justify-content-between mb-4">
        <div class="col-auto">
            <h3 class="mb-0 fw-bold"><i class="bi bi-bar-chart-line text-primary me-2"></i> Feedback Results Insights</h3>
            <p class="text-muted mb-0">Analytics and average ratings summarized by teacher, subject, and class.</p>
        </div>
        <div class="col-auto d-flex gap-2">
            <a href="{{ url_for('admin.dashboard') }}" class="btn btn-outline-secondary"><i class="bi bi-arrow-left me-1"></i>Back to Dashboard</a>
        </div>
    </div>
    
    <div class="card border-0 shadow-sm mb-4">
        <div class="card-body">
            <form method="GET" action="{{ url_for('admin.feedback_results') }}" class="row g-2 align-items-end">
                <div class="col-md-5">
                    <label class="form-label mb-1 text-muted small fw-bold">Study Year</label>
                    <select name="study_year" class="form-select form-select-sm">
                        {% for y in study_years %}
                        <option value="{{ y }}" {% if selected_year == y %}selected{% endif %}>{{ y }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-5">
                    <label class="form-label mb-1 text-muted small fw-bold">Semester</label>
                    <select name="semester" class="form-select form-select-sm">
                        <option value="">All Semesters</option>
                        <option value="1" {% if selected_sem == '1' %}selected{% endif %}>Semester 1</option>
                        <option value="2" {% if selected_sem == '2' %}selected{% endif %}>Semester 2</option>
                        <option value="3" {% if selected_sem == '3' %}selected{% endif %}>Semester 3</option>
                        <option value="4" {% if selected_sem == '4' %}selected{% endif %}>Semester 4</option>
                    </select>
                </div>
                <div class="col-md-2">
                    <button type="submit" class="btn btn-primary btn-sm w-100"><i class="bi bi-funnel me-1"></i>Filter</button>
                </div>
            </form>
        </div>
    </div>
    
    <div class="card border-0 shadow-sm">
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-hover table-borderless align-middle mb-0" id="resultsTable">
                    <thead class="bg-light border-bottom">
                        <tr>
                            <th class="py-3 px-4 cursor-pointer" onclick="sortTable(0)">Teacher <i class="bi bi-arrow-down-up small text-muted"></i></th>
                            <th class="cursor-pointer" onclick="sortTable(1)">Subject <i class="bi bi-arrow-down-up small text-muted"></i></th>
                            <th class="cursor-pointer" onclick="sortTable(2)">Class (Snapshot) <i class="bi bi-arrow-down-up small text-muted"></i></th>
                            <th class="cursor-pointer" onclick="sortTable(3)">Semester <i class="bi bi-arrow-down-up small text-muted"></i></th>
                            <th class="cursor-pointer" onclick="sortTable(4)">Responses <i class="bi bi-arrow-down-up small text-muted"></i></th>
                            <th class="cursor-pointer" onclick="sortTable(5)">Avg Rating <i class="bi bi-arrow-down-up small text-muted"></i></th>
                            <th class="text-end px-4">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% if summary %}
                            {% for row in summary %}
                            <tr>
                                <td class="py-3 px-4">
                                    <div class="d-flex align-items-center">
                                        <div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center me-3 shadow-sm" style="width: 35px; height: 35px;">{{ row.teacher_name[:1] | default('T', true) | upper }}</div>
                                        <div class="fw-semibold">{{ row.teacher_name }}</div>
                                    </div>
                                </td>
                                <td><span class="badge bg-light text-dark border"><i class="bi bi-book me-1 text-primary"></i>{{ row.subject_name }}</span></td>
                                <td>{{ row.snapshot_class_name or row.snapshot_class_id }}</td>
                                <td><span class="badge bg-secondary">Sem {{ row.semester }}</span></td>
                                <td><span class="badge bg-info text-white rounded-pill px-2">{{ row.response_count }}</span></td>
                                <td>
                                    <h6 class="mb-0 {% if row.avg_rating != 'N/A' and row.avg_rating >= 4.0 %}text-success{% elif row.avg_rating != 'N/A' and row.avg_rating >= 2.5 %}text-primary{% else %}text-danger{% endif %} fw-bold">
                                        <i class="bi bi-star-fill me-1 small"></i>
                                        {{ row.avg_rating }} <small class="text-muted fw-normal" style="font-size: 0.75rem;">/ 5.0</small>
                                    </h6>
                                </td>
                                <td class="text-end px-4">
                                    <a href="{{ url_for('admin.feedback_teacher_details', teacher_id=row.teacher_id, subject_id=row.subject_id, study_year=selected_year) }}" class="btn btn-sm btn-outline-primary rounded-pill px-3">
                                        <i class="bi bi-list-columns-reverse me-1"></i> Details
                                    </a>
                                </td>
                            </tr>
                            {% endfor %}
                        {% else %}
                            <tr><td colspan="7" class="text-center py-5 text-muted"><i class="bi bi-inbox fs-2 d-block mb-2 text-secondary opacity-50"></i>No feedback results found for the selected criteria.</td></tr>
                        {% endif %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<script>
function sortTable(n) {
  var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
  table = document.getElementById("resultsTable");
  switching = true;
  dir = "asc"; 
  while (switching) {
    switching = false;
    rows = table.rows;
    for (i = 1; i < (rows.length - 1); i++) {
      shouldSwitch = false;
      x = rows[i].getElementsByTagName("TD")[n];
      y = rows[i + 1].getElementsByTagName("TD")[n];
      var xContent = x.textContent || x.innerText;
      var yContent = y.textContent || y.innerText;
      
      // Parse numbers if applicable
      if (!isNaN(parseFloat(xContent)) && !isNaN(parseFloat(yContent))) {
          xContent = parseFloat(xContent);
          yContent = parseFloat(yContent);
      } else {
          xContent = xContent.toLowerCase();
          yContent = yContent.toLowerCase();
      }

      if (dir == "asc") {
        if (xContent > yContent) {
          shouldSwitch = true;
          break;
        }
      } else if (dir == "desc") {
        if (xContent < yContent) {
          shouldSwitch = true;
          break;
        }
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
<style>
.cursor-pointer { cursor: pointer; user-select: none; }
.cursor-pointer:hover { background-color: #f1f3f5 !important; }
</style>
{% endblock %}
"""

with open('templates/admin/feedback/results.html', 'w', encoding='utf-8') as f:
    f.write(new_html)
print("SUCCESS!")
