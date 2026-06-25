from pathlib import Path
p = Path('templates/profile/_sidebar.html')
content = p.read_text(encoding='utf-8')
content = content.replace('<a class="profile-side-link" href="#"><i class="bi bi-clipboard2-check"></i><span>QAP Results</span></a>', '<a class="profile-side-link {{ \'active\' if active == \'qap\' else \'\' }}" href="{{ url_for(\'profile.qap_results\') }}"><i class="bi bi-clipboard2-check"></i><span>QAP Results</span></a>')
content = content.replace('<a class="profile-side-link" href="#"><i class="bi bi-chat-square-text"></i><span>Appeals</span></a>', '<a class="profile-side-link {{ \'active\' if active == \'appeals\' else \'\' }}" href="{{ url_for(\'profile.appeals\') }}"><i class="bi bi-chat-square-text"></i><span>Appeals</span></a>')
p.write_text(content, encoding='utf-8')
print("Sidebar updated")
