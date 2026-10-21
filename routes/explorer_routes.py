"""
Database Explorer Routes - Allows interactive table schema exploration,
metadata inspection, and server-side paginated record browsing.
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from services.database_explorer_service import DatabaseExplorerService

explorer_bp = Blueprint('explorer', __name__)

@explorer_bp.route('/explorer')
def index():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))

    tables_res = DatabaseExplorerService.get_tables_summary()
    tables = tables_res.get("tables", []) if tables_res.get("success") else []
    return render_template('explorer.html', tables=tables)

@explorer_bp.route('/api/explorer/tables')
def api_tables():
    if not session.get('user_id'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return jsonify(DatabaseExplorerService.get_tables_summary())

@explorer_bp.route('/api/explorer/table/<table_name>')
def api_table_details(table_name):
    if not session.get('user_id'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return jsonify(DatabaseExplorerService.get_table_details(table_name))

@explorer_bp.route('/api/explorer/data/<table_name>')
def api_table_data(table_name):
    if not session.get('user_id'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    search = request.args.get('search', '', type=str)
    sort_by = request.args.get('sort_by', None, type=str)
    sort_dir = request.args.get('sort_dir', 'ASC', type=str)

    res = DatabaseExplorerService.get_paginated_records(
        table_name=table_name,
        page=page,
        per_page=per_page,
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir
    )
    return jsonify(res)
