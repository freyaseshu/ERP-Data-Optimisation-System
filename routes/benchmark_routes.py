"""
Performance Benchmarking Routes - Demonstrates ERP database query tuning,
runs repeatable baseline vs optimised comparisons, and tracks historical metrics.
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from services.benchmark_service import BenchmarkService, BENCHMARK_WORKLOAD
from utils.decorators import role_required

benchmark_bp = Blueprint('benchmark', __name__)

@benchmark_bp.route('/benchmarks')
def index():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))

    env = BenchmarkService.get_environment_info()
    history = BenchmarkService.get_benchmark_history(limit=15)
    return render_template('benchmarks.html', workload=BENCHMARK_WORKLOAD, environment=env, history=history)

@benchmark_bp.route('/api/benchmarks/run', methods=['POST'])
@role_required('Admin')
def api_run_benchmarks():
    if not session.get('user_id'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    data = request.get_json() or {}
    if data.get('confirm') is not True:
        return jsonify(success=False, error='confirm=true is required to approve the shown indexes.'), 400
    item_id = data.get('id')
    iterations = data.get('iterations', 3)
    if type(iterations) is not int or not 1 <= iterations <= 10:
        return jsonify(success=False, error='iterations must be an integer from 1 to 10.'), 400

    if item_id:
        # Run specific benchmark item
        item = next((b for b in BENCHMARK_WORKLOAD if b.get('id') == item_id), None)
        if not item:
            return jsonify({"success": False, "error": f"Benchmark item '{item_id}' not found"}), 404
        
        result = BenchmarkService.run_benchmark_item(item, apply_index=True, iterations=iterations)
        return jsonify(result), 200 if result.get('success') else 400
    else:
        # Run all benchmarks
        results = BenchmarkService.run_all_benchmarks(iterations=iterations)
        return jsonify(results)

@benchmark_bp.route('/api/benchmarks/history')
def api_history():
    if not session.get('user_id'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    limit = request.args.get('limit', 50, type=int)
    history = BenchmarkService.get_benchmark_history(limit=limit)
    return jsonify({"success": True, "history": history})
