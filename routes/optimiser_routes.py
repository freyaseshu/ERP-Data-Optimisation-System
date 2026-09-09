from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from services.query_optimizer import QueryOptimizerService

optimiser_bp = Blueprint('optimiser', __name__)

@optimiser_bp.route('/optimiser', methods=['GET'])
def index():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
        
    return render_template('optimiser.html')

@optimiser_bp.route('/api/optimise-query', methods=['POST'])
def optimise_query_api():
    if not session.get('user_id'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
        
    data = request.get_json()
    query = data.get('query')
    
    if not query:
        return jsonify({"success": False, "error": "Query is required"}), 400
        
    # First measure execution time before any optimization
    time_before, error = QueryOptimizerService.measure_execution_time(query)
    if error:
        return jsonify({"success": False, "error": error}), 400
        
    result = QueryOptimizerService.generate_suggestions(query)
    if result.get("success"):
        result["execution_time_before"] = round(time_before, 4)
        
    return jsonify(result)

@optimiser_bp.route('/api/apply-optimization', methods=['POST'])
def apply_optimization_api():
    if not session.get('user_id'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
        
    data = request.get_json()
    optimization_sql = data.get('optimization_sql')
    original_query = data.get('original_query')
    
    if not optimization_sql or not original_query:
        return jsonify({"success": False, "error": "Missing parameters"}), 400
        
    result = QueryOptimizerService.apply_optimization(optimization_sql, original_query)
    
    return jsonify(result)
