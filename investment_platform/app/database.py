"""
Database Module - Plain SQLAlchemy Setup

Provides database engine, session management, and base model class
without Flask-SQLAlchemy dependency.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

# Create declarative base for models
Base = declarative_base()

# Database engine and session (initialized later)
_engine = None
_session_factory = None
_Session = None


def get_database_url():
    """
    Get database URL from environment or config.

    Returns:
        Database connection string
    """
    # Check for DB2 configuration first
    db2_dsn = os.getenv('DB2_DSN')
    if db2_dsn:
        uid = os.getenv('DB2_UID', '')
        pwd = os.getenv('DB2_PWD', '')
        hostname = os.getenv('DB2_HOSTNAME', 'localhost')
        port = os.getenv('DB2_PORT', '50000')
        database = os.getenv('DB2_DATABASE', '')

        return f"ibm_db_sa://{uid}:{pwd}@{hostname}:{port}/{database}"

    # Fall back to DATABASE_URL or SQLite
    return os.getenv('DATABASE_URL', 'sqlite:///investment_platform.db')


def init_db(app=None, database_url=None):
    """
    Initialize the database engine and session.

    Args:
        app: Flask application (optional, for config)
        database_url: Override database URL
    """
    global _engine, _session_factory, _Session

    if database_url is None:
        if app and 'SQLALCHEMY_DATABASE_URI' in app.config:
            database_url = app.config['SQLALCHEMY_DATABASE_URI']
        else:
            database_url = get_database_url()

    # Create engine with connection pooling
    engine_kwargs = {
        'pool_pre_ping': True,  # Verify connections before use
    }

    # SQLite doesn't support pool settings
    if not database_url.startswith('sqlite'):
        engine_kwargs.update({
            'pool_size': 5,
            'max_overflow': 10,
            'pool_timeout': 30,
            'pool_recycle': 1800,
        })

    _engine = create_engine(database_url, **engine_kwargs)
    _session_factory = sessionmaker(bind=_engine)
    _Session = scoped_session(_session_factory)

    # Bind session to Base for query property
    Base.query = _Session.query_property()

    return _engine


def get_engine():
    """Get the database engine."""
    global _engine
    if _engine is None:
        init_db()
    return _engine


def get_session():
    """
    Get a database session.

    Returns:
        SQLAlchemy session instance
    """
    global _Session
    if _Session is None:
        init_db()
    return _Session()


def get_scoped_session():
    """
    Get the scoped session factory.

    Returns:
        Scoped session
    """
    global _Session
    if _Session is None:
        init_db()
    return _Session


def create_all():
    """Create all database tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)


def drop_all():
    """Drop all database tables."""
    engine = get_engine()
    Base.metadata.drop_all(engine)


def close_session():
    """Close and remove the current session."""
    global _Session
    if _Session:
        _Session.remove()


class DatabaseSession:
    """
    Context manager for database sessions.

    Usage:
        with DatabaseSession() as session:
            session.query(Model).all()
    """

    def __init__(self):
        self.session = None

    def __enter__(self):
        self.session = get_session()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.session.rollback()
        else:
            self.session.commit()
        return False


# Convenience alias
db_session = get_scoped_session
