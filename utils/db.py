"""
Central SQLAlchemy instance, shared across models and app factory.
Kept in its own module to avoid circular imports between app.py and models/.
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
