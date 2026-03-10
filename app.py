"""
MIS Institute Management System — Application Entry Point
All routes live in blueprints/; this file is the thin app factory.
"""
from flask import Flask, request
from datetime import datetime
import os
import gzip as _gzip
import db
from config import config

# ── File-upload constants (shared with teacher blueprint via app.config) ──────
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx',
    'txt', 'zip', 'rar', 'jpg', 'jpeg', 'png', 'gif'
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def create_app():
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 3600
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
    app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # ── Gzip compression ──────────────────────────────────────────────────────
    @app.after_request
    def compress_response(response):
        """Gzip responses >1KB for text/HTML/JSON content types."""
        if (response.status_code < 200 or response.status_code >= 300
                or response.direct_passthrough
                or 'gzip' not in request.accept_encodings):
            return response
        content_type = response.content_type or ''
        if not any(ct in content_type for ct in ('text/', 'application/json', 'application/javascript')):
            return response
        data = response.get_data()
        if len(data) < 1400:
            return response
        compressed = _gzip.compress(data, compresslevel=6)
        response.set_data(compressed)
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Content-Length'] = len(compressed)
        response.vary.add('Accept-Encoding')
        return response

    # ── Context processor — available in every template ───────────────────────
    @app.context_processor
    def inject_user():
        """Make user info available to all templates."""
        from flask import session
        context = {'now': datetime.now}
        if 'user_id' in session:
            context['current_user'] = {
                'id': session.get('user_id'),
                'username': session.get('username'),
                'full_name': session.get('full_name'),
                'role': session.get('role')
            }
        else:
            context['current_user'] = None
        return context

    # ── Template filter ───────────────────────────────────────────────────────
    @app.template_filter('replace_section')
    def replace_section_filter(text):
        """Replace 'Section' with 'Class' and fix UTF-8 double-encoding artifacts."""
        if text:
            text = text.replace('Section', 'Class')
            text = text.replace('\u00c2\u00b7', '\u00b7')
            text = text.replace('\u00e2\u0080\u0093', '\u2013')
            text = text.replace('\u00e2\u0080\u0094', '\u2014')
            text = text.replace('\u00c2\u00a0', ' ')
        return text

    # ── Register blueprints ───────────────────────────────────────────────────
    from blueprints.auth import auth_bp
    from blueprints.admin import admin_bp
    from blueprints.teacher import teacher_bp
    from blueprints.student import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(student_bp)

    return app


app = create_app()


def init_admin():
    """Create default admin user if not exists."""
    from werkzeug.security import generate_password_hash
    admin = db.get_user_by_username('admin')
    if not admin:
        password_hash = generate_password_hash('admin123')
        db.create_user('admin', password_hash, 'System Administrator', 'admin', 'admin@mis.edu', 'admin123')
        print("Default admin created. Username: admin, Password: admin123")
    db.ensure_exam_notes_column()



if __name__ == '__main__':
    init_admin()
    app.run(debug=True, host='0.0.0.0', port=5000)
