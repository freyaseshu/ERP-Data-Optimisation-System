"""
Data Archive routes.
"""
from flask import Blueprint, jsonify, render_template, request, session
from utils.decorators import login_required, role_required
from services.archive_service import preview_archive, execute_archive, ARCHIVABLE_TABLES

archive_bp = Blueprint('archive', __name__)


@archive_bp.route('/archive')
@login_required
def archive_page():
    return render_template('archive.html', tables=list(ARCHIVABLE_TABLES.keys()))


@archive_bp.route('/api/archive/preview', methods=['POST'])
@login_required
def archive_preview():
    data = request.get_json(silent=True) or {}
    table = data.get('table')
    before_date = data.get('before_date')

    if not table or not before_date:
        return jsonify({"success": False, "message": "table and before_date are required.", "data": {}}), 400

    try:
        result = preview_archive(table, before_date)
        return jsonify({"success": True, "message": "Archive preview generated.", "data": result}), 200
    except ValueError as e:
        return jsonify({"success": False, "message": str(e), "data": {}}), 400
    except Exception as e:
        return jsonify({"success": False, "message": "Archive preview failed.", "data": {}}), 500


@archive_bp.route('/api/archive/execute', methods=['POST'])
@role_required('Admin')
def archive_execute():
    data = request.get_json(silent=True) or {}
    table = data.get('table')
    before_date = data.get('before_date')
    confirm = data.get('confirm', False)

    if confirm is not True:
        return jsonify({
            "success": False, "message": "Archiving requires explicit confirmation (confirm=true).", "data": {}
        }), 400

    if not table or not before_date:
        return jsonify({"success": False, "message": "table and before_date are required.", "data": {}}), 400

    try:
        result = execute_archive(table, before_date, session.get('username', 'unknown'))
        return jsonify({"success": True, "message": result.get("message", "Archived."), "data": result}), 200
    except ValueError as e:
        return jsonify({"success": False, "message": str(e), "data": {}}), 400
    except Exception as e:
        return jsonify({"success": False, "message": "Archive operation failed.", "data": {}}), 500

@archive_bp.route('/api/archive/history')
@login_required
def history():
    from models.archive_log import ArchiveLog
    logs = ArchiveLog.query.order_by(ArchiveLog.id.desc()).limit(100)
    return jsonify(success=True, logs=[{'table_name': r.table_name, 'records_archived': r.records_archived, 'archive_date': r.archive_date.isoformat(), 'archived_by': r.archived_by} for r in logs])
