with open('templates/admin/feedback/teacher_details.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("Avg: {{ student.avg_rating }}", "{% if student.avg_rating == 'N/A' %}Not Submitted{% else %}Avg: {{ student.avg_rating }}{% endif %}")

with open('templates/admin/feedback/teacher_details.html', 'w', encoding='utf-8') as f:
    f.write(text)
