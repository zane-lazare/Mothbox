"""
Configuration module for Mothbox Web UI
Handles environment-specific settings for development and production
"""
import os


class Config:
    """Base configuration"""
    # Flask settings
    # SECRET_KEY must be set in production for session security
    SECRET_KEY = os.environ.get('SECRET_KEY')

    if not SECRET_KEY:
        # Only allow fallback in development/testing
        if os.environ.get('MOTHBOX_ENV', 'production').lower() == 'production':
            raise RuntimeError(
                "SECRET_KEY environment variable must be set in production!\n"
                "Generate a secure key with: python3 -c 'import secrets; print(secrets.token_hex(32))'\n"
                "Then set it with: export SECRET_KEY='your-generated-key'"
            )
        # Development fallback
        SECRET_KEY = 'dev-secret-key-change-in-production'
    elif SECRET_KEY == 'dev-secret-key-change-in-production':
        # Prevent using the dev default in production
        if os.environ.get('MOTHBOX_ENV', 'production').lower() == 'production':
            raise RuntimeError(
                "The development default SECRET_KEY cannot be used in production!\n"
                "Generate a secure key with: python3 -c 'import secrets; print(secrets.token_hex(32))'\n"
                "Then set it with: export SECRET_KEY='your-generated-key'"
            )

    # CSRF Protection settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No time limit for single-user device
    WTF_CSRF_CHECK_DEFAULT = True  # Check all POST/PUT/DELETE/PATCH by default

    # Application settings
    HOST = '0.0.0.0'
    PORT = 5000

    # CORS settings - restrict origins for security
    # Can be overridden via ALLOWED_ORIGINS environment variable (comma-separated)
    CORS_ORIGINS = []


class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    TESTING = True
    ENV_NAME = 'development'

    # Development server is acceptable in this mode
    ALLOW_DEV_SERVER = True

    # Verbose logging for debugging
    LOG_LEVEL = 'DEBUG'

    # CSRF optional in development for easier testing
    # Set to False if you want to test without CSRF during development
    WTF_CSRF_ENABLED = True

    # CORS: Allow all origins in development for remote access to Pi
    # Allows testing from any IP address (e.g., accessing Pi via 192.168.x.x)
    # Can still be overridden via ALLOWED_ORIGINS env var for specific origins
    allowed_origins_env = os.environ.get('ALLOWED_ORIGINS', '*')
    CORS_ORIGINS = '*' if allowed_origins_env == '*' else allowed_origins_env.split(',')


class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    TESTING = False
    ENV_NAME = 'production'

    # Development server not recommended but supported for backward compatibility
    # TODO: Enforce gunicorn when issue #19 is implemented
    ALLOW_DEV_SERVER = True  # Will become False after issue #19

    # Minimal logging in production
    LOG_LEVEL = 'INFO'

    # CORS: Restrictive by default in production
    # Only allow same-origin requests unless ALLOWED_ORIGINS is explicitly set
    # For production with separate frontend, set ALLOWED_ORIGINS env var
    CORS_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '').split(',') if os.environ.get('ALLOWED_ORIGINS') else []


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}


def get_config():
    """Get configuration based on MOTHBOX_ENV environment variable"""
    env = os.environ.get('MOTHBOX_ENV', 'production').lower()
    return config.get(env, config['default'])
