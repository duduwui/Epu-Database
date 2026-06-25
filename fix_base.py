
import sys
content = open('templates/base.html', encoding='utf-8').read()
content = content.replace('url_for(\'profile.edit\')', 'url_for(\'profile.dashboard\')')
with open('templates/base.html', 'w', encoding='utf-8') as f:
    f.write(content)

