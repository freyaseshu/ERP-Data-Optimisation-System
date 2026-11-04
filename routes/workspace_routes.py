import json
from flask import Blueprint, Response, jsonify, render_template, request, session
from utils.db import db
from utils.decorators import login_required, role_required
from models.optimization_run import OptimizationRun
from services.optimization_workspace import PROFILES, assess, decide

workspace_bp = Blueprint('workspace', __name__)


@workspace_bp.route('/workspace')
@login_required
def index():
    return render_template('workspace.html', profiles=PROFILES)


@workspace_bp.route('/api/workspace/runs', methods=['GET', 'POST'])
@login_required
def runs():
    if request.method == 'POST':
        try:
            return jsonify(success=True, run=assess(request.get_json(), session.get('username', 'unknown'))), 201
        except ValueError as exc:
            return jsonify(success=False, error=str(exc)), 400
    rows = OptimizationRun.query.order_by(OptimizationRun.id.desc()).limit(30).all()
    return jsonify(success=True, runs=[{'id': r.id, 'profile': r.profile, 'created_at': r.created_at.isoformat(),
        'created_by': r.created_by, 'statuses': [a['status'] for a in r.actions]} for r in rows])


@workspace_bp.route('/api/workspace/runs/<int:run_id>')
@login_required
def get_run(run_id):
    row = db.session.get(OptimizationRun, run_id)
    if row is None:
        return jsonify(success=False, error='Workspace run not found.'), 404
    return jsonify(success=True, run=row.to_dict())


@workspace_bp.route('/api/workspace/runs/<int:run_id>/export')
@login_required
def export(run_id):
    row = db.session.get(OptimizationRun, run_id)
    if row is None:
        return jsonify(success=False, error='Workspace run not found.'), 404
    return Response(json.dumps(row.to_dict(), indent=2), mimetype='application/json',
                    headers={'Content-Disposition': f'attachment; filename=erp-workspace-{run_id}.json'})


@workspace_bp.route('/api/workspace/runs/<int:run_id>/actions/<key>', methods=['POST'])
@role_required('Admin')
def action_decision(run_id, key):
    data = request.get_json()
    if set(data) - {'decision', 'confirm'} or data.get('decision') not in ('approve', 'reject'):
        return jsonify(success=False, error='Provide decision=approve or reject; client SQL is not accepted.'), 400
    if data.get('decision') == 'approve' and data.get('confirm') is not True:
        return jsonify(success=False, error='Review this action and provide confirm=true.'), 400
    try:
        result = decide(run_id, key, data['decision'], session.get('username', 'unknown'))
        return jsonify(result), 200 if result['success'] else 400
    except ValueError as exc:
        return jsonify(success=False, error=str(exc)), 400
