"""
Configuration file for MIS Institute Management System
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""

    # SECRET_KEY signs all session cookies.
    # A known/weak key lets anyone forge an admin session without logging in.
    # Always set this in .env — never rely on the fallback in production.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'mis-system-secret-key-change-in-production'

    # Fernet symmetric key — used to encrypt the plain_password column so
    # admins can still see what password they set, but the DB stores it encrypted.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    FERNET_KEY = os.environ.get('FERNET_KEY') or None

    # PostgreSQL Database Configuration
    DB_HOST = os.environ.get('DB_HOST') or 'localhost'
    DB_PORT = os.environ.get('DB_PORT') or '5432'
    DB_NAME = os.environ.get('DB_NAME') or 'mis_system'
    DB_USER = os.environ.get('DB_USER') or 'postgres'
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or 'your_password_here'

    # Database connection string
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    # Session configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

    @classmethod
    def validate(cls):
        """Call this at startup in production to catch missing critical env vars."""
        if cls.SECRET_KEY == 'mis-system-secret-key-change-in-production':
            raise RuntimeError(
                "SECRET_KEY is not set or is still the default value. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if not cls.FERNET_KEY:
            raise RuntimeError(
                "FERNET_KEY is not set. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )


# Use development config by default
config = DevelopmentConfig()
