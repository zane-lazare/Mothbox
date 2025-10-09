"""
Configuration module for Mothbox Web UI
Handles environment-specific settings for development and production
"""
import os


class Config:
    """Base configuration"""
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Application settings
    HOST = '0.0.0.0'
    PORT = 5000


class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    TESTING = True
    ENV_NAME = 'development'

    # Development server is acceptable in this mode
    ALLOW_DEV_SERVER = True

    # Verbose logging for debugging
    LOG_LEVEL = 'DEBUG'


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
