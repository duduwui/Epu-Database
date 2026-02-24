"""
Quick fix script for attendance_summary.html template syntax errors.
Run this if the template gets broken again by auto-formatting.
"""
import re

template_file = r"templates\admin\attendance_summary.html"

print("Fixing attendance_summary.html template syntax...")

with open(template_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix semester dropdown
content = re.sub(
    r'{% if selected_semester="" ="sem" %}',
    '{% if selected_semester == sem %}',
    content
)

# Fix shift dropdown
content = re.sub(
    r'{% if selected_shift="" ="shift" %}',
    '{% if selected_shift == shift %}',
    content
)

# Fix section dropdown (multi-line broken format)
content = re.sub(
    r'{%\s*if\s*selected_section=""\s*="section"\s*%}selected{%\s*endif\s*%}',
    '{% if selected_section == section %}selected{% endif %}',
    content,
    flags=re.DOTALL
)

with open(template_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Template fixed!")
print("The following corrections were made:")
print("  - Line ~21: {% if selected_semester == sem %}")
print("  - Line ~32: {% if selected_shift == shift %}")
print("  - Line ~45: {% if selected_section == section %}")
