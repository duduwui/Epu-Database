import re

with open('templates/admin/enrollment_periods.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Action column modification
old_action = """<td class="text-center">
                        <form method="POST" action="{{ url_for('admin.delete_enrollment_period', period_id=period.id) }}" class="enroll-delete-form" style="display:inline;">
                          <button type="submit" class="btn btn-sm btn-outline-danger" title="Delete"><i class="bi bi-trash"></i></button>
                        </form>
                      </td>"""

new_action = """<td class="text-center">
                        <button type="button" class="btn btn-sm btn-outline-info me-1" data-bs-toggle="modal" data-bs-target="#enrollRosterModal{{ period.id }}" title="View Roster">
                          <i class="bi bi-people"></i>
                        </button>
                        <form method="POST" action="{{ url_for('admin.delete_enrollment_period', period_id=period.id) }}" class="enroll-delete-form" style="display:inline;">
                          <button type="submit" class="btn btn-sm btn-outline-danger" title="Delete"><i class="bi bi-trash"></i></button>
                        </form>
                      </td>"""

if old_action in text:
    text = text.replace(old_action, new_action)

# Add Modals
old_loop_end = """                    {% endfor %}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        {% endif %}
      {% endfor %}"""

new_loop_end = """                    {% endfor %}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <!-- Modals for this semester's enrollment periods -->
          {% for period in sem_periods %}
          <div class="modal fade" id="enrollRosterModal{{ period.id }}" tabindex="-1">
            <div class="modal-dialog modal-xl modal-dialog-scrollable">
              <div class="modal-content">
                <div class="modal-header bg-light border-bottom border-primary border-top-0 border-end-0 border-start-0 border-3">
                  <div>
                    <h5 class="modal-title fw-bold text-primary mb-1">
                      <i class="bi bi-people-fill me-2 text-primary"></i>Enrollment Roster
                    </h5>
                    <div class="text-muted small">
                      <i class="bi bi-calendar-range me-1"></i>Semester {{ period.semester }} Enrollment
                    </div>
                  </div>
                  <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body p-0">
                  <!-- Stats Header -->
                  <div class="bg-white border-bottom p-3">
                    <div class="row text-center g-3">
                      <div class="col-4 border-end">
                        <div class="fs-4 fw-bold text-dark">{{ period.signup_summary.total_students }}</div>
                        <small class="text-muted">Total Students</small>
                      </div>
                      <div class="col-4 border-end">
                        <div class="fs-4 fw-bold text-success">{{ period.signup_summary.assigned_count }}</div>
                        <small class="text-muted"><i class="bi bi-check-circle me-1"></i>Enrolled</small>
                      </div>
                      <div class="col-4">
                        <div class="fs-4 fw-bold text-warning">{{ period.signup_summary.pending_count }}</div>
                        <small class="text-muted"><i class="bi bi-clock me-1"></i>Pending</small>
                      </div>
                    </div>
                  </div>

                  <!-- Table Filters -->
                  <div class="bg-light border-bottom p-3 filter-bar">
                    <div class="row g-2 align-items-center">
                      <div class="col-md-4">
                        <div class="input-group input-group-sm">
                          <span class="input-group-text bg-white bg-opacity-75 border-end-0"><i class="bi bi-search text-muted"></i></span>
                          <input type="text" class="form-control border-start-0 ps-0 text-navy fw-medium" id="enrollSearchInput{{ period.id }}" placeholder="Search by student name..." onkeyup="filterEnrollRoster({{ period.id }})">
                        </div>
                      </div>
                      <div class="col-md-4">
                        <div class="input-group input-group-sm">
                          <span class="input-group-text bg-white bg-opacity-75 text-muted"><i class="bi bi-funnel"></i>&nbsp;Status</span>
                          <select class="form-select text-navy fw-medium" id="enrollStatusFilter{{ period.id }}" onchange="filterEnrollRoster({{ period.id }})">
                            <option value="all">All Students</option>
                            <option value="assigned">Enrolled</option>
                            <option value="pending">Pending</option>
                          </select>
                        </div>
                      </div>
                      <div class="col-md-4">
                        <div class="input-group input-group-sm">
                          <span class="input-group-text bg-white bg-opacity-75 text-muted"><i class="bi bi-clock-history"></i>&nbsp;Shift</span>
                          <select class="form-select text-navy fw-medium" id="enrollShiftFilter{{ period.id }}" onchange="filterEnrollRoster({{ period.id }})">
                            <option value="all">All Shifts</option>
                            <option value="morning">Morning</option>
                            <option value="evening">Evening</option>
                          </select>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Roster Table -->
                  <div class="table-responsive">
                    <table class="table table-hover table-sm mb-0 align-middle" id="enrollRosterTable{{ period.id }}">
                      <thead class="table-light sticky-top shadow-sm" style="z-index: 10;">
                        <tr>
                          <th class="ps-3 text-muted small text-uppercase">Number</th>
                          <th class="text-muted small text-uppercase">Name</th>
                          <th class="text-muted small text-uppercase">Shift</th>
                          <th class="text-muted small text-uppercase">Class</th>
                          <th class="text-muted small text-uppercase">Status</th>
                          <th class="text-end pe-3 text-muted small text-uppercase">Subjects Enrolled</th>
                        </tr>
                      </thead>
                      <tbody>
                        {% if period.signup_summary.all_rows %}
                          {% for student in period.signup_summary.all_rows %}
                          <tr class="student-row bg-white border-bottom">
                            <td class="ps-3"><span class="badge bg-light text-dark border">{{ student.student_number }}</span></td>
                            <td class="student-name fw-medium text-navy">{{ student.student_name }}</td>
                            <td class="student-shift"><span class="badge {% if student.shift == 'morning' %}bg-warning-subtle text-warning border border-warning-subtle{% else %}bg-indigo-subtle text-info border border-info-subtle{% endif %}"><i class="bi {% if student.shift == 'morning' %}bi-brightness-alt-high-fill{% else %}bi-moon-stars-fill{% endif %} me-1"></i>{{ student.shift|title }}</span></td>
                            <td><small class="text-muted"><i class="bi bi-person-workspace me-1"></i>{{ student.class_name or 'Unassigned' }}</small></td>
                            <td class="student-status" data-status="{{ 'assigned' if student.is_assigned else 'pending' }}">
                              {% if student.is_assigned %}
                                <span class="badge bg-success-subtle text-success border border-success ps-2 pe-3 py-1 rounded-pill"><i class="bi bi-check-circle-fill me-1"></i>Enrolled</span>
                              {% else %}
                                <span class="badge bg-warning-subtle text-warning border border-warning ps-2 pe-3 py-1 rounded-pill"><i class="bi bi-exclamation-circle-fill me-1"></i>Pending</span>
                              {% endif %}
                            </td>
                            <td class="text-end pe-3">
                              <span class="badge {% if student.signup_count > 0 %}bg-primary{% else %}bg-light text-muted border{% endif %} rounded-pill fs-7 px-3 py-1">
                                {{ student.signup_count }} subjects
                              </span>
                            </td>
                          </tr>
                          {% endfor %}
                        {% else %}
                          <tr>
                            <td colspan="6" class="text-center py-5 text-muted">
                              <i class="bi bi-people display-4 d-block mb-3 text-black-50"></i>
                              No students found for this semester.
                            </td>
                          </tr>
                        {% endif %}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          </div>
          {% endfor %}
        {% endif %}
      {% endfor %}"""

if old_loop_end in text:
    text = text.replace(old_loop_end, new_loop_end)

# Also add JS function for filtering enrollment
js_func = """<script>
function filterRoster(periodId) {
  // Exam period filter (already exists)
  ...
"""

old_js = """<script>
function filterRoster(periodId) {"""

new_js = """<script>
function filterEnrollRoster(periodId) {
  const query = document.getElementById('enrollSearchInput' + periodId).value.toLowerCase();
  const status = document.getElementById('enrollStatusFilter' + periodId).value;
  const shift = document.getElementById('enrollShiftFilter' + periodId).value;

  const table = document.getElementById('enrollRosterTable' + periodId);
  if (!table) return;

  const rows = table.getElementsByClassName('student-row');

  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    const nameNode = row.querySelector('.student-name');
    const name = nameNode ? nameNode.textContent.toLowerCase() : '';
    
    let matchQuery = (name.indexOf(query) > -1);

    const shiftNode = row.querySelector('.student-shift');
    const rowShift = shiftNode ? shiftNode.textContent.trim().toLowerCase() : '';
    let matchShift = (shift === 'all' || rowShift === shift);

    const statusNode = row.querySelector('.student-status');
    const rowStatus = statusNode ? statusNode.getAttribute('data-status') : '';
    let matchStatus = (status === 'all' || rowStatus === status);

    if (matchQuery && matchStatus && matchShift) {
      row.style.display = '';
    } else {
      row.style.display = 'none';
    }
  }
}

function filterRoster(periodId) {"""

if old_js in text:
    text = text.replace(old_js, new_js)

with open('templates/admin/enrollment_periods.html', 'w', encoding='utf-8') as f:
    f.write(text)
