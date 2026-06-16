from pathlib import Path

profile_py = Path("blueprints/profile.py")
content = profile_py.read_text(encoding="utf-8")

if "def qap_results():" not in content:
    extras = '''

@profile_bp.route('/qap-results', methods=['GET'])
@teacher_required
def qap_results():
    teacher_user_id = _current_teacher_user_id()
    teacher = _teacher_or_redirect()
    if not teacher: return redirect(url_for('auth.login'))
    return render_template('profile/qap_results.html', teacher=teacher)

@profile_bp.route('/appeals', methods=['GET'])
@teacher_required
def appeals():
    teacher_user_id = _current_teacher_user_id()
    teacher = _teacher_or_redirect()
    if not teacher: return redirect(url_for('auth.login'))
    return render_template('profile/appeals.html', teacher=teacher)
'''
    content += extras
    profile_py.write_text(content, encoding="utf-8")
    print("Added routes for QAP and Appeals")
