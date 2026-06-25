import os
from datetime import datetime
from pathlib import Path

from flask import Blueprint, Response, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

import db
from blueprints.auth import teacher_required


profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

PHOTO_EXTENSIONS = {'jpg', 'jpeg', 'png'}
DOCUMENT_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'docx'}
ATTACHMENT_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'docx'}
SOCIAL_TYPES = (
    'Google Scholar',
    'ResearchGate',
    'LinkedIn',
    'Arab Scientists',
    'Scopus',
    'ORCID',
    'Personal Website',
    'Other',
)

CAD_SECTIONS = {
    'seminar': {
        'table': 'seminars',
        'title': 'Seminars',
        'active': 'cad',
        'api_base': '/profile/api/cad',
        'columns': [('title', 'Title'), ('present_type', 'Present Type'), ('number_of_attend', 'Number of Attend'), ('attachment', 'Attachments')],
        'fields': [
            {'name': 'title', 'label': 'Title', 'type': 'text', 'required': True},
            {'name': 'present_type', 'label': 'Present Type', 'type': 'select', 'required': True, 'options': ['National', 'International']},
            {'name': 'number_of_attend', 'label': 'Number of Attend', 'type': 'number', 'required': True},
            {'name': 'date', 'label': 'Date', 'type': 'date', 'required': True},
        ],
    },
    'workshop': {
        'table': 'workshops',
        'title': 'Workshop',
        'active': 'cad',
        'api_base': '/profile/api/cad',
        'attend_form': True,
        'columns': [('present_national', 'Present/National'), ('present_international', 'Present/International'), ('number_of_attend', 'Number of Attend'), ('attachment', 'Attachments')],
        'fields': [
            {'name': 'present_national', 'label': 'Present/National', 'type': 'text', 'required': True},
            {'name': 'present_international', 'label': 'Present/International', 'type': 'text', 'required': True},
            {'name': 'number_of_attend', 'label': 'Number of Attend', 'type': 'number', 'required': True},
            {'name': 'date', 'label': 'Date', 'type': 'date', 'required': True},
        ],
    },
    'conference': {
        'table': 'conferences',
        'title': 'Conferences',
        'active': 'cad',
        'api_base': '/profile/api/cad',
        'columns': [('title', 'Title'), ('place', 'Place'), ('participation_type', 'Type'), ('attachment', 'Attachments')],
        'fields': [
            {'name': 'title', 'label': 'Conference Title', 'type': 'text', 'required': True},
            {'name': 'link', 'label': 'Link', 'type': 'url'},
            {'name': 'place', 'label': 'Place', 'type': 'text'},
            {'name': 'country', 'label': 'Country', 'type': 'text', 'required': True},
            {'name': 'participation_type', 'label': 'Participation Type', 'type': 'select', 'required': True, 'options': ['Managing a Panel/Keynote speaker', 'Submitting a Research', 'Participate as a guest', 'Other']},
            {'name': 'date', 'label': 'Date', 'type': 'date', 'required': True},
        ],
    },
    'training': {
        'table': 'trainings',
        'title': 'Trainings',
        'active': 'cad',
        'api_base': '/profile/api/cad',
        'columns': [('title', 'Title'), ('participation_type', 'Type'), ('level', 'Level'), ('start_date', 'Start Date'), ('end_date', 'End Date'), ('attachment', 'Attachments')],
        'fields': [
            {'name': 'title', 'label': 'Training Title', 'type': 'text', 'required': True},
            {'name': 'place', 'label': 'Place', 'type': 'text'},
            {'name': 'participation_type', 'label': 'Participation Type', 'type': 'select', 'required': True, 'options': ['Participate as an instructor', 'Participate as a trainee']},
            {'name': 'level', 'label': 'Level', 'type': 'select', 'required': True, 'options': ['Local', 'National', 'International']},
            {'name': 'start_date', 'label': 'Start Date', 'type': 'date', 'required': True},
            {'name': 'end_date', 'label': 'End Date', 'type': 'date', 'required': True},
        ],
    },
    'committee': {
        'table': 'committees',
        'title': 'Committees',
        'active': 'cad',
        'api_base': '/profile/api/cad',
        'columns': [('name', 'Title'), ('level', 'Level'), ('attachment', 'Attachments')],
        'fields': [
            {'name': 'name', 'label': 'Committee Name', 'type': 'text', 'required': True},
            {'name': 'level', 'label': 'Level', 'type': 'select', 'required': True, 'options': ['Ministry', 'University', 'Specific Committee', 'College/Institute']},
        ],
    },
    'research-evaluation': {
        'table': 'research_evaluations',
        'title': 'Research Evaluations',
        'active': 'cad',
        'api_base': '/profile/api/cad',
        'columns': [('from_source', 'From'), ('level', 'Level'), ('date', 'Date'), ('attachment', 'Attachments')],
        'fields': [
            {'name': 'from_source', 'label': 'From', 'type': 'text', 'required': True},
            {'name': 'level', 'label': 'Level', 'type': 'select', 'required': True, 'options': ['Local', 'National', 'International']},
            {'name': 'date', 'label': 'Date', 'type': 'date', 'required': True},
        ],
    },
    'activity': {
        'table': 'activities',
        'title': 'Activities',
        'active': 'cad',
        'api_base': '/profile/api/cad',
        'columns': [('title', 'Title'), ('activity_type', 'Type'), ('link', 'Link'), ('date', 'Date'), ('attachment', 'Attachments')],
        'fields': [
            {'name': 'title', 'label': 'Title', 'type': 'text', 'required': True},
            {'name': 'activity_type', 'label': 'Type', 'type': 'select', 'required': True, 'options': ['Interviews', 'Media Appearance', 'Community Service', 'Other']},
            {'name': 'link', 'label': 'Link', 'type': 'url'},
            {'name': 'date', 'label': 'Date', 'type': 'date', 'required': True},
        ],
    },
    'evaluation-committee': {
        'table': 'evaluation_committees',
        'title': 'Evaluation Committee',
        'active': 'cad',
        'api_base': '/profile/api/cad',
        'columns': [('department', 'Department'), ('degree', 'Degree'), ('attachment', 'Attachments')],
        'fields': [
            {'name': 'department', 'label': 'Department', 'type': 'text', 'required': True},
            {'name': 'degree', 'label': 'Degree', 'type': 'select', 'required': True, 'options': ['Bachelor of Science', 'Master of Science', 'Doctor of Philosophy']},
        ],
    },
}

PORTFOLIO_SECTIONS = {
    'teaching': {
        'table': 'teachings',
        'title': 'Courses',
        'active': 'portfolio',
        'group_label': 'Portfolio',
        'api_base': '/profile/api/portfolio',
        'columns': [('subject', 'Subject'), ('level', 'Level'), ('stage', 'Stage'), ('attachment', 'Attachments')],
        'fields': [
            {'name': 'subject', 'label': 'Subject', 'type': 'text', 'required': True},
            {'name': 'department', 'label': 'Department', 'type': 'text', 'required': True},
            {'name': 'number_of_hours', 'label': 'Number of Hours', 'type': 'number', 'required': True},
            {'name': 'level', 'label': 'Level', 'type': 'select', 'required': True, 'options': ['Undergraduate', 'Postgraduate']},
            {'name': 'stage', 'label': 'Stage', 'type': 'select', 'required': True, 'options': ['First Stage', 'Second Stage', 'Third Stage', 'Fourth Stage']},
            {'name': 'link', 'label': 'Link', 'type': 'url'},
            {'name': 'date', 'label': 'Date', 'type': 'date', 'required': True},
        ],
    },
    'supervision': {
        'table': 'supervisions',
        'title': 'Supervision',
        'active': 'portfolio',
        'group_label': 'Portfolio',
        'api_base': '/profile/api/portfolio',
        'columns': [('research_title', 'Research Title'), ('degree_type', 'Degree Type'), ('date', 'Date'), ('attachment', 'Attachments')],
        'fields': [
            {'name': 'research_title', 'label': 'Research Title', 'type': 'text', 'required': True},
            {'name': 'department', 'label': 'Department', 'type': 'text', 'required': True},
            {'name': 'degree_type', 'label': 'Degree Type', 'type': 'select', 'required': True, 'options': ['Bachelor of Science', 'Master of Science', 'Doctor of Philosophy']},
            {'name': 'date', 'label': 'Date', 'type': 'date', 'required': True},
        ],
    },
    'acknowledgement': {
        'table': 'acknowledgements',
        'title': 'Acknowledgments',
        'active': 'portfolio',
        'group_label': 'Portfolio',
        'api_base': '/profile/api/portfolio',
        'columns': [('from_source', 'From'), ('date', 'Date'), ('attachment', 'Attachments')],
        'fields': [
            {'name': 'from_source', 'label': 'From', 'type': 'select', 'required': True, 'options': ['Ministry', 'University', 'College/Institute', 'International']},
            {'name': 'date', 'label': 'Date', 'type': 'date', 'required': True},
        ],
    },
    'membership': {
        'table': 'memberships',
        'title': 'Memberships',
        'active': 'portfolio',
        'group_label': 'Portfolio',
        'api_base': '/profile/api/portfolio',
        'columns': [('organization_name', 'Organization Name'), ('level', 'Level'), ('date', 'Date'), ('attachment', 'Attachments')],
        'fields': [
            {'name': 'organization_name', 'label': 'Name of Organization or Association', 'type': 'text', 'required': True},
            {'name': 'link', 'label': 'Link', 'type': 'url'},
            {'name': 'level', 'label': 'Level', 'type': 'select', 'required': True, 'options': ['Local', 'National', 'International']},
            {'name': 'date', 'label': 'Date', 'type': 'date', 'required': True},
        ],
    },
}


def _current_teacher_user_id():
    return session.get('user_id')


def _teacher_or_redirect():
    teacher = db.get_teacher_profile(_current_teacher_user_id())
    if not teacher:
        flash('Teacher profile not found.', 'danger')
        return None
    return teacher


def _teacher_upload_dir(user_id):
    upload_dir = Path(current_app.root_path) / 'static' / 'uploads' / f'teacher_{user_id}'
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _save_upload(file_storage, user_id, allowed_extensions):
    if not file_storage or not file_storage.filename:
        return None
    original_name = secure_filename(file_storage.filename)
    extension = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else ''
    if extension not in allowed_extensions:
        raise ValueError('Unsupported file type.')
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{original_name}"
    file_storage.save(_teacher_upload_dir(user_id) / filename)
    return f"uploads/teacher_{user_id}/{filename}"


def _delete_static_file(relative_path):
    if not relative_path:
        return
    target = (Path(current_app.root_path) / 'static' / relative_path).resolve()
    static_root = (Path(current_app.root_path) / 'static').resolve()
    try:
        target.relative_to(static_root)
    except ValueError:
        return
    if target.exists() and target.is_file():
        target.unlink()


def _json_error(message, status=400):
    return jsonify({'ok': False, 'error': message}), status



RESEARCH_SECTIONS = {
    'research': {
        'table': 'researches',
        'title': 'Researches',
        'active': 'researches',
        'group_label': 'Researches',
        'api_base': '/profile/api/researches',
        'columns': [('title', 'Title'), ('publication_status', 'Status'), ('publication_type', 'Type'), ('date', 'Date'), ('attachment', 'Attachments')],
        'fields': [
            {'name': 'title', 'label': 'Title', 'type': 'text', 'required': True},
            {'name': 'publication_status', 'label': 'Publication Status', 'type': 'select', 'required': True, 'options': ['Published', 'Under Review', 'In Progress']},
            {'name': 'publication_type', 'label': 'Publication Type', 'type': 'select', 'required': True, 'options': ['Impact factor Journal', 'Non-Impact factor Journal', 'Conference Paper', 'Book Chapter']},
            {'name': 'journal_name_and_number', 'label': 'Journal Name and Number', 'type': 'text'},
            {'name': 'published_research_link', 'label': 'Published Research Link', 'type': 'url'},
            {'name': 'doi_link', 'label': 'DOI Link', 'type': 'url'},
            {'name': 'date', 'label': 'Date', 'type': 'date', 'required': True},
        ],
    },
    'book': {
        'table': 'books',
        'title': 'Books',
        'active': 'researches',
        'group_label': 'Researches',
        'api_base': '/profile/api/researches',
        'columns': [('title', 'Title'), ('publisher', 'Publisher'), ('date', 'Date'), ('attachment', 'Attachments')],
        'fields': [
            {'name': 'title', 'label': 'Title', 'type': 'text', 'required': True},
            {'name': 'publisher', 'label': 'Publisher', 'type': 'text', 'required': True},
            {'name': 'date', 'label': 'Date', 'type': 'date', 'required': True},
        ],
    },
    'grant': {
        'table': 'grants',
        'title': 'Grants',
        'active': 'researches',
        'group_label': 'Researches',
        'api_base': '/profile/api/researches',
        'columns': [('title', 'Title Name'), ('grant_type', 'Type'), ('achievement', 'Achievement'), ('date', 'Date'), ('attachment', 'Attachments')],
        'fields': [
            {'name': 'title', 'label': 'Title', 'type': 'text', 'required': True},
            {'name': 'grant_type', 'label': 'Grant Type', 'type': 'text', 'required': True},
            {'name': 'achievement', 'label': 'Achievement', 'type': 'text', 'required': True},
            {'name': 'date', 'label': 'Date', 'type': 'date', 'required': True},
        ],
    },
}

def _section_config_or_404(section):
    return CAD_SECTIONS.get(section) or PORTFOLIO_SECTIONS.get(section) or RESEARCH_SECTIONS.get(section) or RESEARCH_SECTIONS.get(section)


def _attachment_icon(path):
    if not path:
        return ''
    extension = path.rsplit('.', 1)[-1].lower() if '.' in path else ''
    if extension == 'pdf':
        return '🔴'
    if extension in {'doc', 'docx'}:
        return '🟡'
    return '🖼️'


@profile_bp.app_template_filter('attachment_icon')
def attachment_icon_filter(path):
    return _attachment_icon(path)


@profile_bp.route('/dashboard', methods=['GET'])
@teacher_required
def dashboard():
    teacher_user_id = _current_teacher_user_id()
    teacher = _teacher_or_redirect()
    if not teacher:
        return redirect(url_for('auth.dashboard'))

    # Collect stats and announcements
    profile_stats = db.get_teacher_profile_stat_counts(teacher_user_id)
    announcements = db.get_active_announcements(limit=8)

    return render_template(
        'profile/dashboard.html',
        teacher=teacher,
        profile_stats=profile_stats,
        announcements=announcements
    )


@profile_bp.route('/edit', methods=['GET', 'POST'])
@teacher_required
def edit():
    teacher = _teacher_or_redirect()
    if not teacher:
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        first_name = (request.form.get('first_name') or '').strip()
        middle_name = (request.form.get('middle_name') or '').strip()
        last_name = (request.form.get('last_name') or '').strip()
        full_name = ' '.join(part for part in (first_name, middle_name, last_name) if part).strip()
        if not full_name:
            full_name = teacher.get('full_name') or session.get('full_name')

        db.update_teacher_profile(_current_teacher_user_id(), {
            'full_name': full_name,
            'kurdish_full_name': request.form.get('kurdish_full_name'),
            'date_of_birth': request.form.get('date_of_birth'),
            'personal_email': request.form.get('personal_email'),
            'college': request.form.get('college'),
            'department': request.form.get('department'),
            'academic_title': request.form.get('academic_title'),
            'qualification': request.form.get('qualification'),
            'position': request.form.get('position'),
            'status': request.form.get('status'),
            'general_specialization': request.form.get('general_specialization'),
            'specific_specialization': request.form.get('specific_specialization'),
            'gender': request.form.get('gender'),
            'biography': request.form.get('biography'),
            'address': request.form.get('address'),
        })
        session['full_name'] = full_name
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('profile.edit'))

    name_parts = (teacher.get('full_name') or '').split()
    first_name = name_parts[0] if name_parts else ''
    last_name = name_parts[-1] if len(name_parts) > 1 else ''
    middle_name = ' '.join(name_parts[1:-1]) if len(name_parts) > 2 else ''

    return render_template(
        'profile/edit.html',
        teacher=teacher,
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        phones=db.list_teacher_phones(_current_teacher_user_id()),
        socials=db.list_teacher_social_media(_current_teacher_user_id()),
        languages=db.list_teacher_languages(_current_teacher_user_id()),
        social_types=SOCIAL_TYPES,
    )


@profile_bp.route('/photo', methods=['POST'])
@teacher_required
def update_photo():
    teacher = _teacher_or_redirect()
    if not teacher:
        return redirect(url_for('auth.dashboard'))
    try:
        filename = _save_upload(request.files.get('photo'), _current_teacher_user_id(), PHOTO_EXTENSIONS)
        if not filename:
            flash('Choose a photo first.', 'warning')
            return redirect(url_for('profile.edit'))
        _delete_static_file(teacher.get('photo'))
        db.update_teacher_profile_file(_current_teacher_user_id(), 'photo', filename)
        flash('Profile photo updated.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('profile.edit'))


@profile_bp.route('/cv', methods=['POST'])
@teacher_required
def update_cv():
    teacher = _teacher_or_redirect()
    if not teacher:
        return redirect(url_for('auth.dashboard'))
    if request.form.get('delete_cv') == '1':
        _delete_static_file(teacher.get('cv'))
        db.update_teacher_profile_file(_current_teacher_user_id(), 'cv', None)
        flash('CV deleted.', 'success')
        return redirect(url_for('profile.edit'))
    try:
        filename = _save_upload(request.files.get('cv'), _current_teacher_user_id(), DOCUMENT_EXTENSIONS)
        if not filename:
            flash('Choose a CV file first.', 'warning')
            return redirect(url_for('profile.edit'))
        _delete_static_file(teacher.get('cv'))
        db.update_teacher_profile_file(_current_teacher_user_id(), 'cv', filename)
        flash('CV updated.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('profile.edit'))


@profile_bp.route('/change-password', methods=['POST'])
@teacher_required
def change_password():
    teacher = _teacher_or_redirect()
    if not teacher:
        return redirect(url_for('auth.dashboard'))
    current_password = request.form.get('current_password') or ''
    new_password = request.form.get('new_password') or ''
    confirm_password = request.form.get('confirm_password') or ''
    if not check_password_hash(teacher['password_hash'], current_password):
        flash('Current password is incorrect.', 'danger')
    elif len(new_password) < 6:
        flash('New password must be at least 6 characters.', 'danger')
    elif new_password != confirm_password:
        flash('New password and confirmation do not match.', 'danger')
    else:
        db.update_user_password(_current_teacher_user_id(), generate_password_hash(new_password), new_password)
        flash('Password changed successfully.', 'success')
    return redirect(url_for('profile.edit'))


@profile_bp.route('/api/phones', methods=['POST'])
@teacher_required
def add_phone():
    phone_number = (request.json or {}).get('phone_number', '').strip()
    if not phone_number:
        return _json_error('Phone number is required.')
    item_id = db.add_teacher_phone(_current_teacher_user_id(), phone_number)
    return jsonify({'ok': True, 'item': {'id': item_id, 'phone_number': phone_number}})


@profile_bp.route('/api/phones/<int:item_id>', methods=['DELETE'])
@teacher_required
def delete_phone(item_id):
    db.delete_teacher_phone(_current_teacher_user_id(), item_id)
    return jsonify({'ok': True})


@profile_bp.route('/api/social-media', methods=['POST'])
@teacher_required
def add_social_media():
    payload = request.json or {}
    social_type = (payload.get('social_type') or '').strip()
    link = (payload.get('link') or '').strip()
    if social_type not in SOCIAL_TYPES:
        return _json_error('Choose a valid social type.')
    if not link:
        return _json_error('Link is required.')
    item_id = db.add_teacher_social_media(_current_teacher_user_id(), social_type, link)
    return jsonify({'ok': True, 'item': {'id': item_id, 'social_type': social_type, 'link': link}})


@profile_bp.route('/api/social-media/<int:item_id>', methods=['DELETE'])
@teacher_required
def delete_social_media(item_id):
    db.delete_teacher_social_media(_current_teacher_user_id(), item_id)
    return jsonify({'ok': True})


@profile_bp.route('/api/languages', methods=['POST'])
@teacher_required
def add_language():
    language = (request.json or {}).get('language', '').strip()
    if not language:
        return _json_error('Language is required.')
    item_id = db.add_teacher_language(_current_teacher_user_id(), language)
    return jsonify({'ok': True, 'item': {'id': item_id, 'language': language}})


@profile_bp.route('/api/languages/<int:item_id>', methods=['DELETE'])
@teacher_required
def delete_language(item_id):
    db.delete_teacher_language(_current_teacher_user_id(), item_id)
    return jsonify({'ok': True})


@profile_bp.route('/qualification/scientific-title')
@teacher_required
def scientific_titles():
    teacher = _teacher_or_redirect()
    if not teacher:
        return redirect(url_for('auth.dashboard'))
    return render_template(
        'profile/scientific_titles.html',
        teacher=teacher,
        records=db.list_scientific_titles(_current_teacher_user_id()),
    )


@profile_bp.route('/api/scientific-titles', methods=['POST'])
@teacher_required
def add_scientific_title():
    title = (request.form.get('scientific_title') or '').strip()
    university = (request.form.get('university') or '').strip()
    if not title or not university:
        return _json_error('Scientific Title and University are required.')
    try:
        attachment = _save_upload(request.files.get('attachment'), _current_teacher_user_id(), ATTACHMENT_EXTENSIONS)
        item_id = db.add_scientific_title(_current_teacher_user_id(), title, university, attachment)
        return jsonify({'ok': True, 'message': 'The Record Added', 'item': {
            'id': item_id,
            'scientific_title': title,
            'university': university,
            'attachment': attachment,
        }})
    except ValueError as exc:
        return _json_error(str(exc))


@profile_bp.route('/api/scientific-titles/<int:item_id>', methods=['GET'])
@teacher_required
def get_scientific_title(item_id):
    item = db.get_scientific_title(_current_teacher_user_id(), item_id)
    if not item:
        return _json_error('Record not found.', 404)
    return jsonify({'ok': True, 'item': item})


@profile_bp.route('/api/scientific-titles/<int:item_id>', methods=['POST'])
@teacher_required
def update_scientific_title(item_id):
    title = (request.form.get('scientific_title') or '').strip()
    university = (request.form.get('university') or '').strip()
    if not title or not university:
        return _json_error('Scientific Title and University are required.')
    existing = db.get_scientific_title(_current_teacher_user_id(), item_id)
    if not existing:
        return _json_error('Record not found.', 404)
    try:
        attachment = _save_upload(request.files.get('attachment'), _current_teacher_user_id(), ATTACHMENT_EXTENSIONS)
        if attachment:
            _delete_static_file(existing.get('attachment'))
        db.update_scientific_title(_current_teacher_user_id(), item_id, title, university, attachment)
        return jsonify({'ok': True, 'message': 'The Record Updated', 'item': {
            'id': item_id,
            'scientific_title': title,
            'university': university,
            'attachment': attachment or existing.get('attachment'),
        }})
    except ValueError as exc:
        return _json_error(str(exc))


@profile_bp.route('/api/scientific-titles/<int:item_id>', methods=['DELETE'])
@teacher_required
def delete_scientific_title(item_id):
    existing = db.get_scientific_title(_current_teacher_user_id(), item_id)
    if not existing:
        return _json_error('Record not found.', 404)
    _delete_static_file(existing.get('attachment'))
    db.delete_scientific_title(_current_teacher_user_id(), item_id)
    return jsonify({'ok': True, 'message': 'The Record Deleted'})


@profile_bp.route('/cad/<section>')
@teacher_required
def cad_section(section):
    config = _section_config_or_404(section)
    if not config:
        return redirect(url_for('profile.dashboard'))
    teacher = _teacher_or_redirect()
    if not teacher:
        return redirect(url_for('auth.dashboard'))
    return render_template(
        'profile/section_records.html',
        teacher=teacher,
        section=section,
        config=config,
        records=db.list_profile_section_records(_current_teacher_user_id(), config['table']),
    )


@profile_bp.route('/portfolio/<section>')
@teacher_required
def portfolio_section(section):
    config = PORTFOLIO_SECTIONS.get(section)
    if not config:
        return redirect(url_for('profile.dashboard'))
    teacher = _teacher_or_redirect()
    if not teacher:
        return redirect(url_for('auth.dashboard'))
    return render_template(
        'profile/section_records.html',
        teacher=teacher,
        section=section,
        config=config,
        records=db.list_profile_section_records(_current_teacher_user_id(), config['table']),
    )


@profile_bp.route('/api/portfolio/<section>', methods=['POST'])
@teacher_required
def add_portfolio_record(section):
    config = PORTFOLIO_SECTIONS.get(section)
    if not config:
        return _json_error('Unsupported section.', 404)
    values = {}
    for field in config['fields']:
        value = (request.form.get(field['name']) or '').strip()
        if field.get('required') and not value:
            return _json_error(f"{field['label']} is required.")
        values[field['name']] = value or None
    try:
        values['attachment'] = _save_upload(request.files.get('attachment'), _current_teacher_user_id(), ATTACHMENT_EXTENSIONS)
        item_id = db.add_profile_section_record(_current_teacher_user_id(), config['table'], values)
        values['id'] = item_id
        return jsonify({'ok': True, 'message': 'The Record Added', 'item': values})
    except ValueError as exc:
        return _json_error(str(exc))


@profile_bp.route('/api/portfolio/<section>/<int:item_id>', methods=['GET'])
@teacher_required
def get_portfolio_record(section, item_id):
    config = PORTFOLIO_SECTIONS.get(section)
    if not config:
        return _json_error('Unsupported section.', 404)
    item = db.get_profile_section_record(_current_teacher_user_id(), config['table'], item_id)
    if not item:
        return _json_error('Record not found.', 404)
    return jsonify({'ok': True, 'item': item})


@profile_bp.route('/api/portfolio/<section>/<int:item_id>', methods=['POST'])
@teacher_required
def update_portfolio_record(section, item_id):
    config = PORTFOLIO_SECTIONS.get(section)
    if not config:
        return _json_error('Unsupported section.', 404)
    existing = db.get_profile_section_record(_current_teacher_user_id(), config['table'], item_id)
    if not existing:
        return _json_error('Record not found.', 404)
    values = {}
    for field in config['fields']:
        value = (request.form.get(field['name']) or '').strip()
        if field.get('required') and not value:
            return _json_error(f"{field['label']} is required.")
        values[field['name']] = value or None
    try:
        attachment = _save_upload(request.files.get('attachment'), _current_teacher_user_id(), ATTACHMENT_EXTENSIONS)
        if attachment:
            _delete_static_file(existing.get('attachment'))
            values['attachment'] = attachment
        db.update_profile_section_record(_current_teacher_user_id(), config['table'], item_id, values)
        values['id'] = item_id
        values['attachment'] = attachment or existing.get('attachment')
        return jsonify({'ok': True, 'message': 'The Record Updated', 'item': values})
    except ValueError as exc:
        return _json_error(str(exc))


@profile_bp.route('/api/portfolio/<section>/<int:item_id>', methods=['DELETE'])
@teacher_required
def delete_portfolio_record(section, item_id):
    config = PORTFOLIO_SECTIONS.get(section)
    if not config:
        return _json_error('Unsupported section.', 404)
    existing = db.get_profile_section_record(_current_teacher_user_id(), config['table'], item_id)
    if not existing:
        return _json_error('Record not found.', 404)
    _delete_static_file(existing.get('attachment'))
    db.delete_profile_section_record(_current_teacher_user_id(), config['table'], item_id)
    return jsonify({'ok': True, 'message': 'The Record Deleted'})


@profile_bp.route('/researches/<section>')
@teacher_required
def researches_section(section):
    config = RESEARCH_SECTIONS.get(section)
    if not config:
        return redirect(url_for('profile.dashboard'))
    teacher = _teacher_or_redirect()
    if not teacher:
        return redirect(url_for('auth.dashboard'))
    return render_template(
        'profile/section_records.html',
        teacher=teacher,
        section=section,
        config=config,
        records=db.list_profile_section_records(_current_teacher_user_id(), config['table']),
    )


@profile_bp.route('/api/researches/<section>', methods=['POST'])
@teacher_required
def add_researches_record(section):
    config = RESEARCH_SECTIONS.get(section)
    if not config:
        return _json_error('Unsupported section.', 404)
    values = {}
    for field in config['fields']:
        value = (request.form.get(field['name']) or '').strip()
        if field.get('required') and not value:
            return _json_error(f"{field['label']} is required.")
        values[field['name']] = value or None
    try:
        values['attachment'] = _save_upload(request.files.get('attachment'), _current_teacher_user_id(), ATTACHMENT_EXTENSIONS)
        item_id = db.add_profile_section_record(_current_teacher_user_id(), config['table'], values)
        values['id'] = item_id
        return jsonify({'ok': True, 'message': 'The Record Added', 'item': values})
    except ValueError as exc:
        return _json_error(str(exc))


@profile_bp.route('/api/researches/<section>/<int:item_id>', methods=['GET'])
@teacher_required
def get_researches_record(section, item_id):
    config = RESEARCH_SECTIONS.get(section)
    if not config:
        return _json_error('Unsupported section.', 404)
    item = db.get_profile_section_record(_current_teacher_user_id(), config['table'], item_id)
    if not item:
        return _json_error('Record not found.', 404)
    return jsonify({'ok': True, 'item': item})


@profile_bp.route('/api/researches/<section>/<int:item_id>', methods=['POST'])
@teacher_required
def update_researches_record(section, item_id):
    config = RESEARCH_SECTIONS.get(section)
    if not config:
        return _json_error('Unsupported section.', 404)
    existing = db.get_profile_section_record(_current_teacher_user_id(), config['table'], item_id)
    if not existing:
        return _json_error('Record not found.', 404)
    values = {}
    for field in config['fields']:
        value = (request.form.get(field['name']) or '').strip()
        if field.get('required') and not value:
            return _json_error(f"{field['label']} is required.")
        values[field['name']] = value or None
    try:
        attachment = _save_upload(request.files.get('attachment'), _current_teacher_user_id(), ATTACHMENT_EXTENSIONS)
        if attachment:
            _delete_static_file(existing.get('attachment'))
            values['attachment'] = attachment
        db.update_profile_section_record(_current_teacher_user_id(), config['table'], item_id, values)
        values['id'] = item_id
        values['attachment'] = attachment or existing.get('attachment')
        return jsonify({'ok': True, 'message': 'The Record Updated', 'item': values})
    except ValueError as exc:
        return _json_error(str(exc))


@profile_bp.route('/api/researches/<section>/<int:item_id>', methods=['DELETE'])
@teacher_required
def delete_researches_record(section, item_id):
    config = RESEARCH_SECTIONS.get(section)
    if not config:
        return _json_error('Unsupported section.', 404)
    existing = db.get_profile_section_record(_current_teacher_user_id(), config['table'], item_id)
    if not existing:
        return _json_error('Record not found.', 404)
    _delete_static_file(existing.get('attachment'))
    db.delete_profile_section_record(_current_teacher_user_id(), config['table'], item_id)
    return jsonify({'ok': True, 'message': 'The Record Deleted'})


@profile_bp.route('/api/cad/<section>', methods=['POST'])
@teacher_required
def add_cad_record(section):
    config = _section_config_or_404(section)
    if not config:
        return _json_error('Unsupported section.', 404)
    values = {}
    for field in config['fields']:
        value = (request.form.get(field['name']) or '').strip()
        if field.get('required') and not value:
            return _json_error(f"{field['label']} is required.")
        values[field['name']] = value or None
    try:
        values['attachment'] = _save_upload(request.files.get('attachment'), _current_teacher_user_id(), ATTACHMENT_EXTENSIONS)
        item_id = db.add_profile_section_record(_current_teacher_user_id(), config['table'], values)
        values['id'] = item_id
        return jsonify({'ok': True, 'message': 'The Record Added', 'item': values})
    except ValueError as exc:
        return _json_error(str(exc))


@profile_bp.route('/api/cad/<section>/<int:item_id>', methods=['GET'])
@teacher_required
def get_cad_record(section, item_id):
    config = _section_config_or_404(section)
    if not config:
        return _json_error('Unsupported section.', 404)
    item = db.get_profile_section_record(_current_teacher_user_id(), config['table'], item_id)
    if not item:
        return _json_error('Record not found.', 404)
    return jsonify({'ok': True, 'item': item})


@profile_bp.route('/api/cad/<section>/<int:item_id>', methods=['POST'])
@teacher_required
def update_cad_record(section, item_id):
    config = _section_config_or_404(section)
    if not config:
        return _json_error('Unsupported section.', 404)
    existing = db.get_profile_section_record(_current_teacher_user_id(), config['table'], item_id)
    if not existing:
        return _json_error('Record not found.', 404)
    values = {}
    for field in config['fields']:
        value = (request.form.get(field['name']) or '').strip()
        if field.get('required') and not value:
            return _json_error(f"{field['label']} is required.")
        values[field['name']] = value or None
    try:
        attachment = _save_upload(request.files.get('attachment'), _current_teacher_user_id(), ATTACHMENT_EXTENSIONS)
        if attachment:
            _delete_static_file(existing.get('attachment'))
            values['attachment'] = attachment
        db.update_profile_section_record(_current_teacher_user_id(), config['table'], item_id, values)
        values['id'] = item_id
        values['attachment'] = attachment or existing.get('attachment')
        return jsonify({'ok': True, 'message': 'The Record Updated', 'item': values})
    except ValueError as exc:
        return _json_error(str(exc))


@profile_bp.route('/api/cad/<section>/<int:item_id>', methods=['DELETE'])
@teacher_required
def delete_cad_record(section, item_id):
    config = _section_config_or_404(section)
    if not config:
        return _json_error('Unsupported section.', 404)
    existing = db.get_profile_section_record(_current_teacher_user_id(), config['table'], item_id)
    if not existing:
        return _json_error('Record not found.', 404)
    _delete_static_file(existing.get('attachment'))
    db.delete_profile_section_record(_current_teacher_user_id(), config['table'], item_id)
    return jsonify({'ok': True, 'message': 'The Record Deleted'})


@profile_bp.route('/cad/workshop/attend-form')
@teacher_required
def workshop_attend_form():
    teacher = _teacher_or_redirect()
    name = teacher.get('full_name') if teacher else ''
    content = f"Workshop Attendance Form\n\nTeacher: {name}\nDate: __________\nWorkshop: __________\n\nParticipants:\n1.\n2.\n3.\n"
    return Response(
        content,
        mimetype='application/msword',
        headers={'Content-Disposition': 'attachment; filename=workshop_attendance_form.doc'}
    )


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
