"""
System Limitations Service - Tracks all 12 limitations, implementation statuses,
practical solutions, and supporting test evidence.
"""

from utils.db import db
from models.limitation import SystemLimitation

class LimitationsService:
    @classmethod
    def get_all_limitations(cls, status_filter: str = None):
        """
        Retrieves all 12 system limitations, optionally filtered by status.
        """
        query = SystemLimitation.query.order_by(SystemLimitation.id.asc())
        if status_filter and status_filter.strip() and status_filter.lower() != 'all':
            query = query.filter(SystemLimitation.status.ilike(status_filter.strip()))

        limitations = query.all()
        lim_dicts = [l.to_dict() for l in limitations]

        # Calculate counts
        all_lims = SystemLimitation.query.all()
        counts = {
            "total": len(all_lims),
            "implemented": sum(1 for l in all_lims if l.status == "Implemented"),
            "partially_implemented": sum(1 for l in all_lims if l.status == "Partially Implemented"),
            "planned": sum(1 for l in all_lims if l.status == "Planned"),
            "blocked": sum(1 for l in all_lims if l.status == "Blocked")
        }

        return {
            "success": True,
            "limitations": lim_dicts,
            "counts": counts
        }
