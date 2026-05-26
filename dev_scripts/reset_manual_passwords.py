"""Reset passwords for manually created students"""
from werkzeug.security import generate_password_hash
import pg8000
from config import config

# Users to reset with their new passwords
users_to_reset = [
    {"username": "alo", "email": "osa106ss@gmail.com", "new_password": "123456"},
    {"username": "ali hh", "email": "ssg@Gmail.com", "new_password": "123456"},
    {"username": "niga", "email": "niga@fmail.com", "new_password": "123456"},
    {"username": "mis202500001", "new_password": "123456"},
    {"username": "mis202500002", "new_password": "123456"},
    {"username": "mis202500003", "new_password": "123456"},
    {"username": "mis202600001", "new_password": "123456"},
]

conn = pg8000.connect(
    host=config.DB_HOST,
    port=int(config.DB_PORT),
    database=config.DB_NAME,
    user=config.DB_USER,
    password=config.DB_PASSWORD
)
cur = conn.cursor()

print("="*70)
print("RESETTING PASSWORDS FOR MANUALLY CREATED STUDENTS")
print("="*70)
print("\nNew password for all: 123456")
print()

for user_info in users_to_reset:
    username = user_info["username"]
    new_password = user_info["new_password"]
    
    # Hash the password
    password_hash = generate_password_hash(new_password)
    
    # Update in database
    cur.execute(
        "UPDATE users SET password_hash = %s WHERE username = %s",
        (password_hash, username)
    )
    
    email = user_info.get("email", "N/A")
    print(f"✓ Reset password for: {username} ({email})")

conn.commit()
conn.close()

print("\n" + "="*70)
print("DONE! All passwords reset to: 123456")
print("="*70)
print("\nYou can now login with:")
print("  Username: alo")
print("  Password: 123456")
print()
print("Or any other username from the list above with password: 123456")
