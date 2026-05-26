from .core import *

def get_user_by_username(username): return execute_query("SELECT * FROM users WHERE username=%s", (username,), fetch_one=True)

def get_user_by_email(email): return execute_query("SELECT * FROM users WHERE email=%s", (email,), fetch_one=True)

def get_user_by_id(user_id): return execute_query("SELECT * FROM users WHERE id=%s", (user_id,), fetch_one=True)

def create_user(username, password_hash, full_name, role, email=None, plain_password=None, major_id=None):
    return execute_insert_returning("INSERT INTO users (username, password_hash, full_name, role, email, plain_password, major_id) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id", (username, password_hash, full_name, role, email, plain_password, major_id))

def get_all_users(major_id=None):
    if major_id: return execute_query("SELECT id, username, full_name, role, email, created_at, password_hash, plain_password FROM users WHERE major_id=%s ORDER BY id", (major_id,), fetch_all=True)
    return execute_query("SELECT id, username, full_name, role, email, created_at, password_hash, plain_password FROM users ORDER BY id", fetch_all=True)

def delete_user(user_id): return execute_query("DELETE FROM users WHERE id=%s", (user_id,))

def update_user(user_id, full_name, email=None): return execute_query("UPDATE users SET full_name=%s, email=%s WHERE id=%s", (full_name, email, user_id))

def update_user_complete(user_id, username, full_name, email, role): return execute_query("UPDATE users SET username=%s, full_name=%s, email=%s, role=%s WHERE id=%s", (username, full_name, email, role, user_id))

def update_user_password(user_id, password_hash, plain_password=None): return execute_query("UPDATE users SET password_hash=%s, plain_password=%s WHERE id=%s", (password_hash, plain_password, user_id))

def get_teacher_by_user_id(user_id): return execute_query("SELECT t.*, u.full_name, u.username, u.email FROM teachers t JOIN users u ON t.user_id=u.id WHERE t.user_id=%s", (user_id,), fetch_one=True)

def get_student_by_user_id(user_id): return execute_query("SELECT s.*, u.full_name, u.username, u.email, u.major_id, c.name as class_name FROM students s JOIN users u ON s.user_id=u.id LEFT JOIN classes c ON s.class_id=c.id WHERE s.user_id=%s", (user_id,), fetch_one=True)

def assign_major_to_user(user_id, major_id):
    """Assign a user to a major."""
    result = execute_query(
        "UPDATE users SET major_id = %s WHERE id = %s", (major_id, user_id)
    )
    return result
