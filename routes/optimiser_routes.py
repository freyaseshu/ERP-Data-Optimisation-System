from flask import Blueprint, render_template, request, jsonify
from utils.decorators import login_required, role_required
from utils.db import db
from models.optimisation_recommendation import OptimisationRecommendation
from services.query_optimizer import QueryOptimizerService

optimiser_bp = Blueprint('optimiser', __name__)

@optimiser_bp.route('/optimiser')
@login_required
def index():
    return render_template('optimiser.html')

@optimiser_bp.route('/api/optimise-query', methods=['POST'])
@login_required
def optimise_query_api():
    result = QueryOptimizerService.generate_suggestions(request.get_json().get('query'))
    return jsonify(result), 200 if result['success'] else 400

@optimiser_bp.route('/api/apply-optimization', methods=['POST'])
@role_required('Admin')
def apply_optimization_api():
    data = request.get_json()
    if data.get('confirm') is not True or type(data.get('recommendation_id')) is not int:
        return jsonify(success=False, error='An integer recommendation_id and confirm=true are required.'), 400
    result = QueryOptimizerService.apply_optimization(recommendation_id=data['recommendation_id'])
    return jsonify(result), 200 if result['success'] else 400

@optimiser_bp.route('/api/recommendations')
@login_required
def recommendations():
    return jsonify(success=True, recommendations=[r.to_dict() for r in OptimisationRecommendation.query.order_by(OptimisationRecommendation.id.desc()).limit(100)])

@optimiser_bp.route('/api/recommendations/<int:rec_id>/reject', methods=['POST'])
@role_required('Admin')
def reject(rec_id):
    rec = db.session.get(OptimisationRecommendation, rec_id)
    if rec is None or rec.status != 'Pending':
        return jsonify(success=False, error='Pending recommendation not found.'), 404
    rec.status = 'Rejected'
    db.session.commit()
    return jsonify(success=True)
