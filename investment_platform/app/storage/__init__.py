"""
Storage Module - Multi-Backend Data Storage

Supports SQLite, DB2, and CSV file storage backends.
Configure via STORAGE_BACKEND setting in config.
"""
from app.storage.csv_storage import CSVStorage

__all__ = ['CSVStorage']
