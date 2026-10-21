from flask import Blueprint, render_template, request, jsonify
from utils.decorators import login_required
from services.query_analyser import QueryAnalyserService
from services.benchmark_service import BENCHMARK_WORKLOAD

analyser_bp = Blueprint('analyser', __name__)

@analyser_bp.route('/analyser')
@login_required
def index():
    return render_template('analyser.html', predefined_queries=[{'name': b['name'], 'query': b['baseline_sql']} for b in BENCHMARK_WORKLOAD])

@analyser_bp.route('/api/analyse-query', methods=['POST'])
@login_required
def analyse_query_api():
    data = request.get_json()
    if type(data.get('run_analyze', False)) is not bool:
        return jsonify(success=False, error='run_analyze must be boolean.'), 400
    result = QueryAnalyserService.analyze_query(data.get('query'), data.get('run_analyze', False))
    return jsonify(result), 200 if result['success'] else 400

@analyser_bp.route('/api/execute-query', methods=['POST'])
@login_required
def execute_query_api():
    result = QueryAnalyserService.execute_query(request.get_json().get('query'))
    return jsonify(result), 200 if result['success'] else 400
