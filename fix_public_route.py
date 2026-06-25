from pathlib import Path
profile_py = Path("blueprints/profile.py")
content = profile_py.read_text(encoding="utf-8")

if "def public_teacher_profile(" not in content:
    func = '''

@profile_bp.route('/v/<staff_id>')
def public_teacher_profile(staff_id):
    teacher = db.get_teacher_by_staff_id(staff_id)
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return redirect(url_for('public.home'))  # or index
    
    # We will pass all required data to the template
    user_id = teacher['id']
    phones = db.list_teacher_phones(user_id)
    socials = db.list_teacher_social_media(user_id)
    languages = db.list_teacher_languages(user_id)
    scientific_titles = db.list_scientific_titles(user_id)
    
    cad_data = {}
    for section, config in CAD_SECTIONS.items():
        cad_data[section] = {
            'title': config['title'],
            'records': db.list_profile_section_records(user_id, config['table']),
            'columns': config['columns']
        }
        
    portfolio_data = {}
    for section, config in PORTFOLIO_SECTIONS.items():
        portfolio_data[section] = {
            'title': config['title'],
            'records': db.list_profile_section_records(user_id, config['table']),
            'columns': config['columns']
        }
        
    researches_data = {}
    for section, config in RESEARCH_SECTIONS.items():
        researches_data[section] = {
            'title': config['title'],
            'records': db.list_profile_section_records(user_id, config['table']),
            'columns': config['columns']
        }
        
    return render_template('profile/public_profile.html',
                           teacher=teacher,
                           phones=phones,
                           socials=socials,
                           languages=languages,
                           scientific_titles=scientific_titles,
                           cad_data=cad_data,
                           portfolio_data=portfolio_data,
                           researches_data=researches_data)
'''
    content = content + func
    profile_py.write_text(content, encoding="utf-8")
    print("Added public_teacher_profile")
