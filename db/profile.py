from pathlib import Path

from .core import execute_insert_returning, execute_query


PROFILE_TABLES = (
    'teacher_phones',
    'teacher_social_media',
    'teacher_languages',
    'scientific_titles',
    'seminars',
    'workshops',
    'conferences',
    'trainings',
    'committees',
    'research_evaluations',
    'activities',
    'evaluation_committees',
    'teachings',
    'supervisions',
    'acknowledgements',
    'memberships',
    'researches',
    'books',
    'grants',
)


def ensure_teacher_profile_schema():
    migration_path = Path(__file__).resolve().parent.parent / 'database' / 'add_teacher_profile_module.sql'
    return execute_query(migration_path.read_text(encoding='utf-8'))


def ensure_announcements_schema():
    migration_path = Path(__file__).resolve().parent.parent / 'database' / 'add_announcements.sql'
    return execute_query(migration_path.read_text(encoding='utf-8'))


def get_teacher_profile(user_id):
    return execute_query("SELECT * FROM users WHERE id=%s AND role='teacher'", (user_id,), fetch_one=True)


def update_teacher_profile(user_id, data):
    return execute_query(
        """
        UPDATE users
        SET full_name=%s,
            kurdish_full_name=%s,
            date_of_birth=%s,
            personal_email=%s,
            college=%s,
            department=%s,
            academic_title=%s,
            qualification=%s,
            position=%s,
            status=%s,
            general_specialization=%s,
            specific_specialization=%s,
            gender=%s,
            biography=%s,
            address=%s
        WHERE id=%s AND role='teacher'
        """,
        (
            data.get('full_name'),
            data.get('kurdish_full_name'),
            data.get('date_of_birth') or None,
            data.get('personal_email'),
            data.get('college'),
            data.get('department'),
            data.get('academic_title'),
            data.get('qualification'),
            data.get('position'),
            data.get('status'),
            data.get('general_specialization'),
            data.get('specific_specialization'),
            data.get('gender'),
            data.get('biography'),
            data.get('address'),
            user_id,
        )
    )


def update_teacher_profile_file(user_id, column, filename):
    if column not in {'photo', 'cv'}:
        raise ValueError('Invalid profile file column')
    return execute_query(f"UPDATE users SET {column}=%s WHERE id=%s AND role='teacher'", (filename, user_id))


def list_teacher_phones(user_id):
    return execute_query(
        "SELECT id, phone_number FROM teacher_phones WHERE teacher_id=%s ORDER BY id",
        (user_id,),
        fetch_all=True
    ) or []


def add_teacher_phone(user_id, phone_number):
    return execute_insert_returning(
        "INSERT INTO teacher_phones (teacher_id, phone_number) VALUES (%s,%s) RETURNING id",
        (user_id, phone_number)
    )


def delete_teacher_phone(user_id, item_id):
    return execute_query("DELETE FROM teacher_phones WHERE teacher_id=%s AND id=%s", (user_id, item_id))


def list_teacher_social_media(user_id):
    return execute_query(
        "SELECT id, social_type, link FROM teacher_social_media WHERE teacher_id=%s ORDER BY id",
        (user_id,),
        fetch_all=True
    ) or []


def add_teacher_social_media(user_id, social_type, link):
    return execute_insert_returning(
        "INSERT INTO teacher_social_media (teacher_id, social_type, link) VALUES (%s,%s,%s) RETURNING id",
        (user_id, social_type, link)
    )


def delete_teacher_social_media(user_id, item_id):
    return execute_query("DELETE FROM teacher_social_media WHERE teacher_id=%s AND id=%s", (user_id, item_id))


def list_teacher_languages(user_id):
    return execute_query(
        "SELECT id, language FROM teacher_languages WHERE teacher_id=%s ORDER BY id",
        (user_id,),
        fetch_all=True
    ) or []


def add_teacher_language(user_id, language):
    return execute_insert_returning(
        "INSERT INTO teacher_languages (teacher_id, language) VALUES (%s,%s) RETURNING id",
        (user_id, language)
    )


def delete_teacher_language(user_id, item_id):
    return execute_query("DELETE FROM teacher_languages WHERE teacher_id=%s AND id=%s", (user_id, item_id))


def get_teacher_profile_stat_counts(user_id):
    return execute_query(
        """
        SELECT
            (SELECT COUNT(*) FROM researches WHERE teacher_id=%s) AS research,
            (SELECT COUNT(*) FROM books WHERE teacher_id=%s) AS books,
            (SELECT COUNT(*) FROM seminars WHERE teacher_id=%s) AS seminars,
            (SELECT COUNT(*) FROM conferences WHERE teacher_id=%s) AS conferences,
            (SELECT COUNT(*) FROM teachings WHERE teacher_id=%s) AS courses,
            (SELECT COUNT(*) FROM supervisions WHERE teacher_id=%s) AS supervision,
            (SELECT COUNT(*) FROM acknowledgements WHERE teacher_id=%s) AS acknowledgments,
            (SELECT COUNT(*) FROM committees WHERE teacher_id=%s) AS committees
        """,
        (user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id),
        fetch_one=True
    ) or {}


def get_active_announcements(limit=8):
    ensure_announcements_schema()
    return execute_query(
        """
        SELECT id, title, body, published_at, created_at
        FROM announcements
        WHERE is_active = TRUE
        ORDER BY published_at DESC NULLS LAST, created_at DESC, id DESC
        LIMIT %s
        """,
        (limit,),
        fetch_all=True
    ) or []


def list_scientific_titles(user_id):
    return execute_query(
        """
        SELECT id, scientific_title, university, attachment, created_at, updated_at
        FROM scientific_titles
        WHERE teacher_id=%s
        ORDER BY id DESC
        """,
        (user_id,),
        fetch_all=True
    ) or []


def get_scientific_title(user_id, item_id):
    return execute_query(
        """
        SELECT id, scientific_title, university, attachment
        FROM scientific_titles
        WHERE teacher_id=%s AND id=%s
        """,
        (user_id, item_id),
        fetch_one=True
    )


def add_scientific_title(user_id, scientific_title, university, attachment=None):
    return execute_insert_returning(
        """
        INSERT INTO scientific_titles (teacher_id, scientific_title, university, attachment)
        VALUES (%s,%s,%s,%s)
        RETURNING id
        """,
        (user_id, scientific_title, university, attachment)
    )


def update_scientific_title(user_id, item_id, scientific_title, university, attachment=None):
    if attachment is not None:
        return execute_query(
            """
            UPDATE scientific_titles
            SET scientific_title=%s, university=%s, attachment=%s, updated_at=CURRENT_TIMESTAMP
            WHERE teacher_id=%s AND id=%s
            """,
            (scientific_title, university, attachment, user_id, item_id)
        )
    return execute_query(
        """
        UPDATE scientific_titles
        SET scientific_title=%s, university=%s, updated_at=CURRENT_TIMESTAMP
        WHERE teacher_id=%s AND id=%s
        """,
        (scientific_title, university, user_id, item_id)
    )


def delete_scientific_title(user_id, item_id):
    return execute_query("DELETE FROM scientific_titles WHERE teacher_id=%s AND id=%s", (user_id, item_id))


PROFILE_SECTION_FIELDS = {
    'seminars': ['title', 'present_type', 'number_of_attend', 'date', 'attachment'],
    'workshops': ['present_national', 'present_international', 'number_of_attend', 'date', 'attachment'],
    'conferences': ['title', 'link', 'place', 'country', 'participation_type', 'date', 'attachment'],
    'trainings': ['title', 'place', 'participation_type', 'level', 'start_date', 'end_date', 'attachment'],
    'committees': ['name', 'level', 'attachment'],
    'research_evaluations': ['from_source', 'level', 'date', 'attachment'],
    'activities': ['title', 'activity_type', 'link', 'date', 'attachment'],
    'evaluation_committees': ['department', 'degree', 'attachment'],
    'teachings': ['subject', 'department', 'number_of_hours', 'level', 'stage', 'link', 'date', 'attachment'],
    'supervisions': ['research_title', 'department', 'degree_type', 'date', 'attachment'],
    'acknowledgements': ['from_source', 'date', 'attachment'],
    'memberships': ['organization_name', 'link', 'level', 'date', 'attachment'],
}


def _section_fields(table):
    fields = PROFILE_SECTION_FIELDS.get(table)
    if not fields:
        raise ValueError('Unsupported profile section')
    return fields


def list_profile_section_records(user_id, table):
    fields = _section_fields(table)
    return execute_query(
        f"SELECT id, {', '.join(fields)}, created_at, updated_at FROM {table} WHERE teacher_id=%s ORDER BY id DESC",
        (user_id,),
        fetch_all=True
    ) or []


def get_profile_section_record(user_id, table, item_id):
    fields = _section_fields(table)
    return execute_query(
        f"SELECT id, {', '.join(fields)} FROM {table} WHERE teacher_id=%s AND id=%s",
        (user_id, item_id),
        fetch_one=True
    )


def add_profile_section_record(user_id, table, values):
    fields = _section_fields(table)
    columns = [field for field in fields if field in values]
    placeholders = ', '.join(['%s'] * (len(columns) + 1))
    return execute_insert_returning(
        f"INSERT INTO {table} (teacher_id, {', '.join(columns)}) VALUES ({placeholders}) RETURNING id",
        (user_id, *[values.get(field) for field in columns])
    )


def update_profile_section_record(user_id, table, item_id, values):
    fields = _section_fields(table)
    columns = [field for field in fields if field in values]
    assignments = ', '.join([f"{field}=%s" for field in columns])
    return execute_query(
        f"UPDATE {table} SET {assignments}, updated_at=CURRENT_TIMESTAMP WHERE teacher_id=%s AND id=%s",
        (*[values.get(field) for field in columns], user_id, item_id)
    )


def delete_profile_section_record(user_id, table, item_id):
    _section_fields(table)
    return execute_query(f"DELETE FROM {table} WHERE teacher_id=%s AND id=%s", (user_id, item_id))
