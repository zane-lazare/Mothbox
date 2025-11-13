"""
Unit tests for webui/backend/config.py module

Tests configuration classes, SECRET_KEY validation, environment detection,
CORS settings, and the config factory function.
"""
import pytest
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'webui' / 'backend'))


class TestSecretKeyValidation:
    """Test SECRET_KEY validation logic"""

    def test_production_requires_secret_key(self, monkeypatch):
        """Production should raise RuntimeError if SECRET_KEY not set"""
        monkeypatch.delenv('SECRET_KEY', raising=False)
        monkeypatch.setenv('MOTHBOX_ENV', 'production')

        # Clear the module from cache to force re-import
        if 'config' in sys.modules:
            del sys.modules['config']

        with pytest.raises(RuntimeError) as exc_info:
            import config

        assert "SECRET_KEY environment variable must be set in production" in str(exc_info.value)
        assert "python3 -c 'import secrets" in str(exc_info.value)

    def test_production_rejects_dev_default_key(self, monkeypatch):
        """Production should reject the dev default SECRET_KEY"""
        monkeypatch.setenv('SECRET_KEY', 'dev-secret-key-change-in-production')
        monkeypatch.setenv('MOTHBOX_ENV', 'production')

        if 'config' in sys.modules:
            del sys.modules['config']

        with pytest.raises(RuntimeError) as exc_info:
            import config

        assert "development default SECRET_KEY cannot be used in production" in str(exc_info.value)

    def test_production_accepts_custom_secret_key(self, monkeypatch):
        """Production should accept a valid custom SECRET_KEY"""
        monkeypatch.setenv('SECRET_KEY', 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6')
        monkeypatch.setenv('MOTHBOX_ENV', 'production')

        if 'config' in sys.modules:
            del sys.modules['config']

        # Should not raise
        import config
        assert config.Config.SECRET_KEY == 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6'

    def test_development_allows_fallback_key(self, monkeypatch):
        """Development should use fallback key when SECRET_KEY not set"""
        monkeypatch.delenv('SECRET_KEY', raising=False)
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.Config.SECRET_KEY == 'dev-secret-key-change-in-production'

    def test_development_accepts_custom_key(self, monkeypatch):
        """Development should accept custom SECRET_KEY"""
        monkeypatch.setenv('SECRET_KEY', 'custom-dev-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.Config.SECRET_KEY == 'custom-dev-key-12345'

    def test_development_accepts_dev_default_explicitly(self, monkeypatch):
        """Development should allow explicit use of dev default key"""
        monkeypatch.setenv('SECRET_KEY', 'dev-secret-key-change-in-production')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.Config.SECRET_KEY == 'dev-secret-key-change-in-production'


class TestGetConfigFactory:
    """Test get_config() factory function"""

    def test_get_config_development(self, monkeypatch):
        """get_config() should return DevelopmentConfig for MOTHBOX_ENV=development"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        cfg = config.get_config()

        assert cfg == config.DevelopmentConfig
        assert cfg.ENV_NAME == 'development'
        assert cfg.DEBUG is True
        assert cfg.TESTING is True

    def test_get_config_production(self, monkeypatch):
        """get_config() should return ProductionConfig for MOTHBOX_ENV=production"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'production')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        cfg = config.get_config()

        assert cfg == config.ProductionConfig
        assert cfg.ENV_NAME == 'production'
        assert cfg.DEBUG is False
        assert cfg.TESTING is False

    def test_get_config_defaults_to_production(self, monkeypatch):
        """get_config() should default to production when MOTHBOX_ENV not set"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.delenv('MOTHBOX_ENV', raising=False)

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        cfg = config.get_config()

        assert cfg == config.ProductionConfig
        assert cfg.ENV_NAME == 'production'

    def test_get_config_invalid_env_fallback(self, monkeypatch):
        """get_config() should fallback to production for invalid MOTHBOX_ENV"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'staging')  # Invalid environment

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        cfg = config.get_config()

        assert cfg == config.ProductionConfig

    def test_get_config_case_handling(self, monkeypatch):
        """get_config() should handle case variations in MOTHBOX_ENV"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')

        # Test uppercase
        monkeypatch.setenv('MOTHBOX_ENV', 'DEVELOPMENT')
        if 'config' in sys.modules:
            del sys.modules['config']
        import config
        assert config.get_config() == config.DevelopmentConfig

        # Test mixed case
        monkeypatch.setenv('MOTHBOX_ENV', 'Production')
        if 'config' in sys.modules:
            del sys.modules['config']
        import config
        assert config.get_config() == config.ProductionConfig


class TestCORSConfiguration:
    """Test CORS configuration settings"""

    def test_development_cors_wildcard_default(self, monkeypatch):
        """Development should default to CORS wildcard '*'"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')
        monkeypatch.delenv('ALLOWED_ORIGINS', raising=False)

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.DevelopmentConfig.CORS_ORIGINS == '*'

    def test_development_cors_custom_wildcard(self, monkeypatch):
        """Development should respect ALLOWED_ORIGINS='*'"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')
        monkeypatch.setenv('ALLOWED_ORIGINS', '*')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.DevelopmentConfig.CORS_ORIGINS == '*'

    def test_development_cors_single_origin(self, monkeypatch):
        """Development should accept single custom origin"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')
        monkeypatch.setenv('ALLOWED_ORIGINS', 'http://localhost:3000')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.DevelopmentConfig.CORS_ORIGINS == ['http://localhost:3000']

    def test_development_cors_multiple_origins(self, monkeypatch):
        """Development should split multiple origins by comma"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')
        monkeypatch.setenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:8080')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.DevelopmentConfig.CORS_ORIGINS == [
            'http://localhost:3000',
            'http://localhost:8080'
        ]

    def test_production_cors_empty_default(self, monkeypatch):
        """Production should default to empty CORS_ORIGINS"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'production')
        monkeypatch.delenv('ALLOWED_ORIGINS', raising=False)

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.ProductionConfig.CORS_ORIGINS == []

    def test_production_cors_from_environment(self, monkeypatch):
        """Production should use ALLOWED_ORIGINS from environment"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'production')
        monkeypatch.setenv('ALLOWED_ORIGINS', 'https://mothbox.example.com')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.ProductionConfig.CORS_ORIGINS == ['https://mothbox.example.com']

    def test_production_cors_multiple_origins(self, monkeypatch):
        """Production should split multiple origins by comma"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'production')
        monkeypatch.setenv('ALLOWED_ORIGINS', 'https://mothbox1.com,https://mothbox2.com')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.ProductionConfig.CORS_ORIGINS == [
            'https://mothbox1.com',
            'https://mothbox2.com'
        ]

    def test_base_config_cors_empty(self, monkeypatch):
        """Base Config should have empty CORS_ORIGINS"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.Config.CORS_ORIGINS == []


class TestCSRFConfiguration:
    """Test CSRF protection settings"""

    def test_csrf_enabled_by_default(self, monkeypatch):
        """CSRF should be enabled by default in base config"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.Config.WTF_CSRF_ENABLED is True

    def test_csrf_headers_configured(self, monkeypatch):
        """CSRF should accept X-CSRFToken header"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.Config.WTF_CSRF_HEADERS == ['X-CSRFToken']

    def test_csrf_no_time_limit(self, monkeypatch):
        """CSRF tokens should have no time limit"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.Config.WTF_CSRF_TIME_LIMIT is None

    def test_csrf_check_default_true(self, monkeypatch):
        """CSRF check should be enabled by default"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.Config.WTF_CSRF_CHECK_DEFAULT is True

    def test_development_csrf_enabled(self, monkeypatch):
        """Development should have CSRF enabled"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.DevelopmentConfig.WTF_CSRF_ENABLED is True

    def test_production_inherits_csrf(self, monkeypatch):
        """Production should inherit CSRF settings from base"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'production')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        # ProductionConfig doesn't override, so inherits from Config
        assert config.ProductionConfig.WTF_CSRF_ENABLED is True
        assert config.ProductionConfig.WTF_CSRF_HEADERS == ['X-CSRFToken']


class TestConfigInheritance:
    """Test configuration class inheritance"""

    def test_development_inherits_base_config(self, monkeypatch):
        """DevelopmentConfig should inherit from Config"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert issubclass(config.DevelopmentConfig, config.Config)

        # Should inherit HOST and PORT
        assert config.DevelopmentConfig.HOST == '0.0.0.0'
        assert config.DevelopmentConfig.PORT == 5000

    def test_production_inherits_base_config(self, monkeypatch):
        """ProductionConfig should inherit from Config"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'production')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert issubclass(config.ProductionConfig, config.Config)

        # Should inherit HOST and PORT
        assert config.ProductionConfig.HOST == '0.0.0.0'
        assert config.ProductionConfig.PORT == 5000

    def test_development_overrides_debug(self, monkeypatch):
        """DevelopmentConfig should override DEBUG to True"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.DevelopmentConfig.DEBUG is True

    def test_production_debug_false(self, monkeypatch):
        """ProductionConfig should have DEBUG False"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'production')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.ProductionConfig.DEBUG is False


class TestEnvironmentSettings:
    """Test environment-specific settings"""

    def test_development_debug_true(self, monkeypatch):
        """Development should have DEBUG=True"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.DevelopmentConfig.DEBUG is True

    def test_production_debug_false(self, monkeypatch):
        """Production should have DEBUG=False"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'production')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.ProductionConfig.DEBUG is False

    def test_development_testing_true(self, monkeypatch):
        """Development should have TESTING=True"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.DevelopmentConfig.TESTING is True

    def test_production_testing_false(self, monkeypatch):
        """Production should have TESTING=False"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'production')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.ProductionConfig.TESTING is False

    def test_log_level_development(self, monkeypatch):
        """Development should have DEBUG log level"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.DevelopmentConfig.LOG_LEVEL == 'DEBUG'

    def test_log_level_production(self, monkeypatch):
        """Production should have INFO log level"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'production')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.ProductionConfig.LOG_LEVEL == 'INFO'

    def test_development_allows_dev_server(self, monkeypatch):
        """Development should allow dev server"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.DevelopmentConfig.ALLOW_DEV_SERVER is True

    def test_production_allows_dev_server_backward_compat(self, monkeypatch):
        """Production should allow dev server for backward compatibility"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'production')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        # Currently True for backward compatibility (issue #19)
        assert config.ProductionConfig.ALLOW_DEV_SERVER is True

    def test_development_env_name(self, monkeypatch):
        """Development should have ENV_NAME='development'"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.DevelopmentConfig.ENV_NAME == 'development'

    def test_production_env_name(self, monkeypatch):
        """Production should have ENV_NAME='production'"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'production')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.ProductionConfig.ENV_NAME == 'production'


class TestBaseConfigSettings:
    """Test base Config class settings"""

    def test_base_config_host(self, monkeypatch):
        """Base config should bind to all interfaces"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.Config.HOST == '0.0.0.0'

    def test_base_config_port(self, monkeypatch):
        """Base config should use port 5000"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert config.Config.PORT == 5000


class TestConfigDictionary:
    """Test the config dictionary mapping"""

    def test_config_dict_has_development(self, monkeypatch):
        """Config dict should have 'development' key"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert 'development' in config.config
        assert config.config['development'] == config.DevelopmentConfig

    def test_config_dict_has_production(self, monkeypatch):
        """Config dict should have 'production' key"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'production')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert 'production' in config.config
        assert config.config['production'] == config.ProductionConfig

    def test_config_dict_has_default(self, monkeypatch):
        """Config dict should have 'default' key pointing to production"""
        monkeypatch.setenv('SECRET_KEY', 'test-key-12345')
        monkeypatch.setenv('MOTHBOX_ENV', 'development')

        if 'config' in sys.modules:
            del sys.modules['config']

        import config
        assert 'default' in config.config
        assert config.config['default'] == config.ProductionConfig
