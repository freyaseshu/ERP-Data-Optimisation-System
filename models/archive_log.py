from utils.time import utc_now
from models.user import db
from datetime import datetime

class ArchiveLog(db.Model):
    __tablename__ = 'archive_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(50), nullable=False)
    records_archived = db.Column(db.Integer, nullable=False)
    archive_date = db.Column(db.DateTime, default=utc_now)
    archived_by = db.Column(db.String(50))
