from utils.db import db


class LoginThrottle(db.Model):
    """Shared, atomic login-attempt limits; HMAC keys avoid storing raw identifiers."""
    __tablename__ = 'login_throttles'
    bucket = db.Column(db.String(64), primary_key=True)
    attempts = db.Column(db.Integer, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
