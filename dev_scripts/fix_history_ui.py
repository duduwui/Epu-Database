import re

with open('templates/admin/feedback/teacher_history.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Make unique ID
text = text.replace('href="#collapse-student-{{ cls.class_id }}-{{ loop.index }}"', 'href="#collapse-student-{{ loop.parent.loop.parent.loop.index }}-{{ loop.parent.loop.index }}-{{ loop.index }}"')
text = text.replace('id="collapse-student-{{ cls.class_id }}-{{ loop.index }}"', 'id="collapse-student-{{ loop.parent.loop.parent.loop.index }}-{{ loop.parent.loop.index }}-{{ loop.index }}"')

# Improve answering ui
old_ans = '''<div class="d-flex flex-column gap-2">
                            {% for ans in st.answers %}
                            <div class="d-flex justify-content-between align-items-center pb-2 {% if not loop.last %}border-bottom{% endif %}">
                                <span class="text-muted small w-75">{{ ans.question }}</span>
                                <span class="fw-bold {% if ans.rating != 'N/A' and ans.rating|int <= 2 %}text-danger{% else %}text-dark{% endif %}">
                                    {{ ans.rating }}{% if ans.rating != 'N/A' %}/5{% endif %}
                                </span>
                            </div>
                            {% endfor %}
                        </div>'''

new_ans = '''<div class="d-flex flex-column gap-3">
                            {% for ans in st.answers %}
                            <div class="p-3 bg-light rounded border border-light-subtle">
                                <div class="d-flex justify-content-between align-items-start mb-2">
                                    <span class="text-dark fw-medium small lh-sm w-75">{{ ans.question }}</span>
                                    <span class="badge {% if ans.rating != 'N/A' and ans.rating|int >= 4 %}bg-success{% elif ans.rating != 'N/A' and ans.rating|int == 3 %}bg-warning text-dark{% elif ans.rating != 'N/A' %}bg-danger{% else %}bg-secondary{% endif %} fs-6 px-2 py-1 shadow-sm">
                                        {{ ans.rating }}{% if ans.rating != 'N/A' %} / 5{% endif %}
                                    </span>
                                </div>
                                {% if ans.rating != 'N/A' %}
                                <div class="progress" style="height: 6px;">
                                    <div class="progress-bar {% if ans.rating|int >= 4 %}bg-success{% elif ans.rating|int == 3 %}bg-warning{% else %}bg-danger{% endif %}" role="progressbar" style="width: {{ (ans.rating|float / 5.0) * 100 }}%" aria-valuenow="{{ ans.rating }}" aria-valuemin="0" aria-valuemax="5"></div>
                                </div>
                                {% endif %}
                            </div>
                            {% endfor %}
                        </div>'''
text = text.replace(old_ans, new_ans)

with open('templates/admin/feedback/teacher_history.html', 'w', encoding='utf-8') as f:
    f.write(text)
