"""
User Model

Handles user authentication with password hashing.
"""
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, Integer, String, DateTime

from app.database import Base, get_scoped_session, is_csv_backend, get_csv_storage


class User(Base):
    """
    User account for portfolio authentication.

    Attributes:
        id: Primary key
        username: Unique username (3-50 chars, alphanumeric + underscore)
        password_hash: Werkzeug password hash
        created_at: Account creation timestamp
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def get_by_username(cls, username):
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_user_by_username(username)
        session = get_scoped_session()
        user = session.query(cls).filter_by(username=username).first()
        if user:
            return user.to_dict()
        return None

    @classmethod
    def get_by_id(cls, user_id):
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.get_user_by_id(user_id)
        session = get_scoped_session()
        user = session.query(cls).filter_by(id=int(user_id)).first()
        if user:
            return user.to_dict()
        return None

    @classmethod
    def create(cls, username, password):
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.create_user(username, password)
        session = get_scoped_session()
        user = cls(username=username)
        user.set_password(password)
        session.add(user)
        session.commit()
        return user.to_dict()

    @classmethod
    def verify(cls, username, password):
        if is_csv_backend():
            storage = get_csv_storage()
            return storage.verify_user(username, password)
        session = get_scoped_session()
        user = session.query(cls).filter_by(username=username).first()
        if user and user.check_password(password):
            return user.to_dict()
        return None
