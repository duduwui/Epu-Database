"""
Authentication blueprint — login, logout, dashboard redirect, and role decorators.
All other blueprints import their required decorators from here.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from functools import wraps
import db
from i18n import normalize_lang

auth_bp = Blueprint('auth', __name__)


# =============================================
# AUTHENTICATION DECORATORS
# =============================================

def login_required(f):
    """Require any logged-in user."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Require admin role (any admin — major admin or superadmin)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def superadmin_required(f):
    """Require superadmin role: admin with no major (admin@epu.edu.iq)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('auth.dashboard'))
        if session.get('major_id') is not None:
            flash('Access denied. Superadmin only.', 'danger')
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def teacher_required(f):
    """Require teacher or admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') not in ['admin', 'teacher']:
            flash('Access denied. Teacher privileges required.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# =============================================
# AUTHENTICATION ROUTES
# =============================================

@auth_bp.route('/')
def index():
    """Home page — redirect to dashboard if logged in."""
    if 'user_id' in session:
        return redirect(url_for('auth.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if 'user_id' in session:
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter both email and password.', 'warning')
            return render_template('login.html')

        user = db.get_user_by_email(email)

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']

            # Detect major from email: name.XXXXXX@epu.edu.iq (6-digit code)
            # Superadmin (admin@epu.edu.iq) has no dot → major_id = None
            major = None
            if user.get('major_id'):
                major = db.get_major_by_id(user['major_id'])
            if not major:
                local_part = email.split('@')[0]  # e.g. "admin.562781"
                if '.' in local_part:
                    major_code = local_part.rsplit('.', 1)[1]  # e.g. "562781"
                    major = db.get_major_by_code(major_code)
                    if major:
                        # Persist major_id on the user row for future logins
                        db.assign_major_to_user(user['id'], major['id'])
            if major:
                session['major_id'] = major['id']
                session['major_code'] = major['code']
                session['major_name'] = major['name']
            else:
                session['major_id'] = None
                session['major_code'] = None
                session['major_name'] = None

            flash(f'Welcome back, {user["full_name"]}!', 'success')
            return redirect(url_for('auth.dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Logout user."""
    lang = normalize_lang(session.get('lang', 'en'))
    session.clear()
    session['lang'] = lang
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/set-language/<lang>')
def set_language(lang):
    """Switch UI language for current session."""
    session['lang'] = normalize_lang(lang)
    next_url = request.args.get('next') or request.referrer
    if not next_url:
        if 'user_id' in session:
            return redirect(url_for('auth.dashboard'))
        return redirect(url_for('auth.login'))
    return redirect(next_url)


@auth_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard — redirects based on role."""
    role = session.get('role')

    if role == 'admin':
        # Superadmin (no major) goes directly to Majors management
        if not session.get('major_id'):
            return redirect(url_for('admin.majors'))
        return redirect(url_for('admin.dashboard'))
    elif role == 'teacher':
        teacher = db.get_teacher_by_user_id(session.get('user_id'))
        if not teacher:
            lang = normalize_lang(session.get('lang', 'en'))
            session.clear()
            session['lang'] = lang
            flash('Your teacher profile no longer exists. Please log in again.', 'warning')
            return redirect(url_for('auth.login'))
        return redirect(url_for('teacher.dashboard'))
    elif role == 'student':
        student = db.get_student_by_user_id(session.get('user_id'))
        if not student:
            lang = normalize_lang(session.get('lang', 'en'))
            session.clear()
            session['lang'] = lang
            flash('Your student profile no longer exists. Please log in again.', 'warning')
            return redirect(url_for('auth.login'))
        return redirect(url_for('student.dashboard'))

    return render_template('dashboard.html')
def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'student':
            flash('Access denied. Student account required.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated_function
