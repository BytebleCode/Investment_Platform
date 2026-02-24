"""
Configuration Management for Investment Platform

Supports multiple environments: development, testing, production.
Loads sensitive credentials from environment variables.
"""
import os
from datetime import timedelta

# Load environment variables from .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system environment variables


class Config:
    """Base configuration class."""

    # Flask Settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False

    # Database Configuration (DB2)
    DB2_DSN = os.getenv('DB2_DSN', '')
    DB2_UID = os.getenv('DB2_UID', '')
    DB2_PWD = os.getenv('DB2_PWD', '')
    DB2_DATABASE = os.getenv('DB2_DATABASE', '')
    DB2_HOSTNAME = os.getenv('DB2_HOSTNAME', 'localhost')
    DB2_PORT = os.getenv('DB2_PORT', '50000')

    # SQLAlchemy Configuration
    # For DB2: ibm_db_sa://user:password@host:port/database
    # For SQLite fallback (development): sqlite:///investment_platform.db
    @property
    def SQLALCHEMY_DATABASE_URI(self):
        if self.DB2_DSN:
            # IBM DB2 connection string
            return f"ibm_db_sa://{self.DB2_UID}:{self.DB2_PWD}@{self.DB2_HOSTNAME}:{self.DB2_PORT}/{self.DB2_DATABASE}"
        else:
            # SQLite fallback for local development
            return os.getenv('DATABASE_URL', 'sqlite:///investment_platform.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Set to True to log SQL queries

    # DB2 Connection Pool Settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'max_overflow': 10,
        'pool_timeout': 30,
        'pool_recycle': 1800,  # Recycle connections after 30 minutes
    }

    # Session Configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # API Settings
    API_BASE_URL = os.getenv('API_BASE_URL', '/api')
    JSON_SORT_KEYS = False

    # Market Data Settings
    YAHOO_FINANCE_CACHE_HOURS = int(os.getenv('YAHOO_FINANCE_CACHE_HOURS', '24'))
    MARKET_DATA_BATCH_SIZE = int(os.getenv('MARKET_DATA_BATCH_SIZE', '5'))
    RATE_LIMIT_DELAY_SECONDS = float(os.getenv('RATE_LIMIT_DELAY_SECONDS', '2'))
    MARKET_DATA_HISTORY_YEARS = int(os.getenv('MARKET_DATA_HISTORY_YEARS', '5'))

    # Trading Settings
    DEFAULT_INITIAL_VALUE = 100000.00
    DEFAULT_TAX_RATE = 0.37  # 37% short-term capital gains
    TRADE_FEE_RATE = 0.001  # 0.1% trading fee

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # Storage Backend: 'sqlite', 'db2', or 'csv'
    STORAGE_BACKEND = os.getenv('STORAGE_BACKEND', 'sqlite')

    # CSV Storage Directory (relative to app root)
    CSV_DATA_DIR = os.getenv('CSV_DATA_DIR', 'data')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = True  # Log SQL queries in development
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        # Use SQLite for local development
        return os.getenv('DATABASE_URL', 'sqlite:///investment_platform.db')


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        # Use in-memory SQLite for tests
        return 'sqlite:///:memory:'

    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False

    # Stricter security in production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Production should always use DB2
    @property
    def SQLALCHEMY_DATABASE_URI(self):
        if not self.DB2_DSN and not self.DB2_UID:
            raise ValueError("Production requires DB2 configuration")
        return f"ibm_db_sa://{self.DB2_UID}:{self.DB2_PWD}@{self.DB2_HOSTNAME}:{self.DB2_PORT}/{self.DB2_DATABASE}"


# Configuration dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get configuration based on FLASK_ENV environment variable."""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])
