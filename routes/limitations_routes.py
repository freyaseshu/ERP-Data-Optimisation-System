"""
System Limitations & Improvements Routes - Dedicated dashboard for tracking
all 12 system limitations, practical solutions, statuses, and test evidence.
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from services.limitations_service import LimitationsService

limitations_bp = Blueprint('limitations', __name__)

@limitations_bp.route('/limitations')
def index():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))

    status_filter = request.args.get('status', 'all')
    res = LimitationsService.get_all_limitations(status_filter=status_filter)

    return render_template(
        'limitations.html',
        limitations=res.get('limitations', []),
        counts=res.get('counts', {}),
        active_filter=status_filter
    )

@limitations_bp.route('/api/limitations')
def api_limitations():
    if not session.get('user_id'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    status_filter = request.args.get('status', 'all')
    res = LimitationsService.get_all_limitations(status_filter=status_filter)
    return jsonify(res)
