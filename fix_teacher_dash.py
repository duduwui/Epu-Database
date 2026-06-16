from pathlib import Path
import re

p_teacher = Path('templates/teacher/dashboard.html')
content = p_teacher.read_text(encoding='utf-8')

# We want to replace the row containing metric-card.
regex = r'<div class="row g-3 mb-4">.*?<div class="row">'
match = re.search(regex, content, flags=re.DOTALL)
if match:
    old_code = match.group(0)
    # the new morph blobs style needed for teacher dashboard
    style_and_cards = '''<style>
  .morph-wrapper {
    display: flex;
    justify-content: center;
  }
  .morph-card {
    position: relative;
    width: 140px;
    height: 180px;
    display: flex;
    align-items: center;
    justify-content: center;
    filter: url(#morphGoo) drop-shadow(0 10px 20px rgba(0,0,0,0.08));
    cursor: pointer;
  }

  /* Основные блобы формируют карточку */
  .morph-blob {
    position: absolute;
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid rgba(255,255,255,0.4);
    border-radius: 50%;
    transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  .morph-blob-1 {
    width: 140px;
    height: 140px;
    top: 20px;
    left: 0;
  }

  .morph-blob-2 {
    width: 80px;
    height: 80px;
    top: -5px;
    left: 30px;
  }

  .morph-blob-3 {
    width: 60px;
    height: 60px;
    bottom: 5px;
    left: 45px;
  }

  /* При hover — блобы перестраиваются */
  .morph-card:hover .morph-blob-1 {
    border-radius: 30%;
    width: 130px;
    height: 130px;
    top: 25px;
    left: 5px;
    transform: rotate(-3deg);
  }

  .morph-card:hover .morph-blob-2 {
    width: 55px;
    height: 55px;
    top: -10px;
    left: -10px;
    transform: rotate(10deg);
  }

  .morph-card:hover .morph-blob-3 {
    width: 45px;
    height: 45px;
    bottom: -15px;
    left: 100px;
    transform: rotate(-8deg);
  }

  /* Контент */
  .morph-content {
    position: relative;
    z-index: 2;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    color: #1C0770;
    transition: all 0.5s ease;
  }

  .morph-icon {
    font-size: 1.8rem;
    color: rgba(28, 7, 112, 0.7);
    transition: all 0.5s ease;
  }

  .morph-card:hover .morph-icon {
    color: #1C0770;
    transform: translateY(-4px);
    filter: drop-shadow(0 0 6px rgba(28, 7, 112, 0.2));
  }

  .morph-label {
    font-family: "Segoe UI", system-ui, sans-serif;
    font-size: 10px;
    font-weight: 600;
    color: rgba(28, 7, 112, 0.6);
    letter-spacing: 1.2px;
    text-transform: uppercase;
    transition: all 0.5s ease;
    text-align: center;
    padding: 0 4px;
    white-space: normal;
  }

  .morph-card:hover .morph-label {
    color: rgba(28, 7, 112, 0.9);
    letter-spacing: 1.5px;
  }

  .morph-count {
    font-family: "Segoe UI", system-ui, sans-serif;
    font-size: 26px;
    font-weight: 500;
    color: #1C0770;
    transition: all 0.5s ease;
  }

  .morph-card:hover .morph-count {
    transform: scale(1.1);
    text-shadow: 0 0 10px rgba(28, 7, 112, 0.15);
  }

  .morph-card:active .morph-blob {
    transform: scale(0.92) !important;
    transition-duration: 0.15s;
  }
</style>

<svg xmlns="http://www.w3.org/2000/svg" version="1.1" style="display:none;width:0;height:0">
  <defs>
    <filter id="morphGoo">
      <feGaussianBlur in="SourceGraphic" stdDeviation="10" result="blur"></feGaussianBlur>
      <feColorMatrix in="blur" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 20 -9" result="goo"></feColorMatrix>
      <feComposite in="SourceGraphic" in2="goo" operator="atop"></feComposite>
    </filter>
  </defs>
</svg>

{% set teacher_dashboard_cards = [
  ('Needing Grades', pending_grade_students or 0, 'bi-clipboard2-x'),
  ('Pending Submissions', pending_submission_count or 0, 'bi-clipboard-check'),
  ('Recent Activity', recent_activity_count or 0, 'bi-activity'),
  ('Attendance Pending', attendance_pending_groups or 0, 'bi-calendar-check')
] %}

<div class="row g-3 mb-5 justify-content-center text-center">
  {% for label, value, icon in teacher_dashboard_cards %}
  <div class="col-6 col-md-3 d-flex justify-content-center">
    <div class="morph-wrapper">
      <div class="morph-card" title="{{ label }}">
        <div class="morph-blob morph-blob-1"></div>
        <div class="morph-blob morph-blob-2"></div>
        <div class="morph-blob morph-blob-3"></div>
        <div class="morph-content">
          <div class="morph-icon"><i class="bi {{ icon }}"></i></div>
          <div class="morph-label">{{ label }}</div>
          <div class="morph-count">{{ value }}</div>
        </div>
      </div>
    </div>
  </div>
  {% endfor %}
</div>

<div class="row">'''
    
    content = content.replace(old_code, style_and_cards)
    p_teacher.write_text(content, encoding='utf-8')
    print("Updated teacher dashboard metric cards")
else:
    print("Could not match the metric cards block in teacher/dashboard")
