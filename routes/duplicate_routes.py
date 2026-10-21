"""
Duplicate Data Checker routes.
"""
from flask import Blueprint, jsonify, render_template, request
from utils.decorators import login_required, role_required
from services.duplicate_checker import find_duplicates, delete_duplicates, TABLE_CONFIG

duplicate_bp = Blueprint('duplicates', __name__)


@duplicate_bp.route('/duplicates')
@login_required
def duplicates_page():
    return render_template('duplicates.html', tables=list(TABLE_CONFIG.keys()))


@duplicate_bp.route('/api/duplicates/<table_name>', methods=['GET'])
@login_required
def get_duplicates(table_name):
    try:
        result = find_duplicates(table_name)
        return jsonify({
            "success": True,
            "message": "Duplicates fetched successfully.",
            "data": result
        }), 200
    except ValueError as e:
        return jsonify({"success": False, "message": str(e), "data": {}}), 400
    except Exception as e:
        return jsonify({"success": False, "message": "Duplicate scan failed.", "data": {}}), 500


@duplicate_bp.route('/api/duplicates/delete', methods=['POST'])
@role_required('Admin')
def delete_duplicates_route():
    data = request.get_json(silent=True) or {}
    table_name = data.get('table')
    keep_id = data.get('keep_id')
    delete_ids = data.get('delete_ids', [])
    confirm = data.get('confirm', False)

    if confirm is not True:
        return jsonify({
            "success": False,
            "message": "Deletion requires explicit confirmation (confirm=true).",
            "data": {}
        }), 400

    if not isinstance(table_name, str) or type(keep_id) is not int or not isinstance(delete_ids, list) or not delete_ids or any(type(i) is not int for i in delete_ids):
        return jsonify({
            "success": False, "message": "table, keep_id and delete_ids are required.", "data": {}
        }), 400

    try:
        deleted_count = delete_duplicates(table_name, int(keep_id), [int(i) for i in delete_ids])
        return jsonify({
            "success": True,
            "message": f"Deleted {deleted_count} duplicate record(s).",
            "data": {"deleted_count": deleted_count}
        }), 200
    except ValueError as e:
        return jsonify({"success": False, "message": str(e), "data": {}}), 400
    except Exception as e:
        return jsonify({"success": False, "message": "Duplicate deletion failed.", "data": {}}), 500
