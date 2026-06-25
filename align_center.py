from pathlib import Path

p = Path('templates/teacher/dashboard.html')
content = p.read_text(encoding='utf-8')

# Center the header
old_header = '<div class="row align-items-center">'
new_header = '<div class="row align-items-center text-center justify-content-center">'
if old_header in content:
    content = content.replace(old_header, new_header)

old_h2 = '<h2><i class="bi bi-grid-1x2 me-2"></i>Teacher Dashboard</h2>'
new_h2 = '<h2 class="fw-bold text-navy"><i class="bi bi-grid-1x2 me-2"></i>Teacher Dashboard</h2>'
if old_h2 in content:
    content = content.replace(old_h2, new_h2)

# Wrap the container in a max-width center if they want it centered broadly
old_container = '<div class="container">'
new_container = '<div class="container" style="max-width: 1180px; margin: 0 auto;">'
if old_container in content:
    content = content.replace(old_container, new_container)

p.write_text(content, encoding='utf-8')
print("Centered the teacher dashboard content")
