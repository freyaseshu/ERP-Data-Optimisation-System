"""
Data Archive routes.
"""
from flask import Blueprint, jsonify, render_template, request, session
from utils.decorators import login_required
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
        return jsonify({"success": False, "message": f"Error previewing archive: {e}", "data": {}}), 500


@archive_bp.route('/api/archive/execute', methods=['POST'])
@login_required
def archive_execute():
    data = request.get_json(silent=True) or {}
    table = data.get('table')
    before_date = data.get('before_date')
    confirm = data.get('confirm', False)

    if not confirm:
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
        return jsonify({"success": False, "message": f"Error executing archive: {e}", "data": {}}), 500
