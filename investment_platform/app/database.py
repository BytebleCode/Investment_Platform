"""
Database Module - Multi-Backend Storage Support

Supports SQLite, DB2, and CSV file storage backends.
Configure via STORAGE_BACKEND in config (sqlite, db2, csv).
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

# Storage backend type
_storage_backend = None
_csv_storage = None


def get_storage_backend():
    """
    Determine which storage backend to use.

    Returns:
        str: 'sqlite', 'db2', or 'csv'
    """
    return os.getenv('STORAGE_BACKEND', 'sqlite').lower()


def is_csv_backend():
    """Check if using CSV storage backend."""
    return get_storage_backend() == 'csv'


def get_csv_storage():
    """Get the CSV storage instance (lazy initialization)."""
    global _csv_storage
    if _csv_storage is None:
        from app.storage.csv_storage import CSVStorage
        data_dir = os.getenv('CSV_DATA_DIR', 'data')
        _csv_storage = CSVStorage(data_dir)
    return _csv_storage


def get_database_url():
    """
    Get database URL from environment or config.

    Returns:
        Database connection string or None if using CSV backend
    """
    backend = get_storage_backend()

    if backend == 'csv':
        return None

    # Check for DB2 configuration
    if backend == 'db2':
        db2_dsn = os.getenv('DB2_DSN')
        if db2_dsn:
            uid = os.getenv('DB2_UID', '')
            pwd = os.getenv('DB2_PWD', '')
            hostname = os.getenv('DB2_HOSTNAME', 'localhost')
            port = os.getenv('DB2_PORT', '50000')
            database = os.getenv('DB2_DATABASE', '')
            return f"ibm_db_sa://{uid}:{pwd}@{hostname}:{port}/{database}"
        else:
            raise ValueError("DB2 backend selected but DB2_DSN not configured")

    # Default to SQLite
    return os.getenv('DATABASE_URL', 'sqlite:///investment_platform.db')


def init_db(app=None, database_url=None):
    """
    Initialize the database engine and session.

    Args:
        app: Flask application (optional, for config)
        database_url: Override database URL
    """
    global _engine, _session_factory, _Session, _storage_backend

    _storage_backend = get_storage_backend()

    # If using CSV backend, no SQLAlchemy initialization needed
    if _storage_backend == 'csv':
        # Initialize CSV storage
        get_csv_storage()
        return None

    if database_url is None:
        if app and 'SQLALCHEMY_DATABASE_URI' in app.config:
            database_url = app.config['SQLALCHEMY_DATABASE_URI']
        else:
            database_url = get_database_url()

    if database_url is None:
        return None

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
    if is_csv_backend():
        return None
    if _engine is None:
        init_db()
    return _engine


def get_session():
    """
    Get a database session.

    Returns:
        SQLAlchemy session instance or None if using CSV backend
    """
    global _Session
    if is_csv_backend():
        return None
    if _Session is None:
        init_db()
    return _Session()


def get_scoped_session():
    """
    Get the scoped session factory.

    Returns:
        Scoped session or None if using CSV backend
    """
    global _Session
    if is_csv_backend():
        return None
    if _Session is None:
        init_db()
    return _Session


def create_all():
    """Create all database tables."""
    if is_csv_backend():
        # CSV files are auto-created by CSVStorage
        get_csv_storage()
        return
    engine = get_engine()
    if engine:
        Base.metadata.create_all(engine)


def drop_all():
    """Drop all database tables."""
    if is_csv_backend():
        # For CSV, we could delete files but that's destructive
        return
    engine = get_engine()
    if engine:
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
        if is_csv_backend():
            return get_csv_storage()
        self.session = get_session()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            if exc_type is not None:
                self.session.rollback()
            else:
                self.session.commit()
        return False


# Convenience alias
db_session = get_scoped_session
