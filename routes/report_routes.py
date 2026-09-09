"""
Performance Reports routes.
"""
from flask import Blueprint, jsonify, render_template, request, Response
from utils.decorators import login_required
from services.performance_service import get_performance_report, export_report_csv

report_bp = Blueprint('reports', __name__)


@report_bp.route('/reports')
@login_required
def reports_page():
    return render_template('reports.html')


@report_bp.route('/api/reports/performance', methods=['GET'])
@login_required
def performance_report():
    range_key = request.args.get('range', '30days')
    start = request.args.get('start')
    end = request.args.get('end')

    try:
        report = get_performance_report(range_key, start, end)
        return jsonify({
            "success": True,
            "message": "Performance report generated.",
            "data": report
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error generating report: {e}", "data": {}}), 500


@report_bp.route('/api/reports/export', methods=['GET'])
@login_required
def export_report():
    range_key = request.args.get('range', '30days')
    start = request.args.get('start')
    end = request.args.get('end')

    try:
        csv_data = export_report_csv(range_key, start, end)
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=performance_report.csv'}
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"Error exporting report: {e}", "data": {}}), 500
