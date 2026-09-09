from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from services.query_analyser import QueryAnalyserService

analyser_bp = Blueprint('analyser', __name__)

@analyser_bp.route('/analyser', methods=['GET', 'POST'])
def index():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
        
    # Predefined queries for user convenience
    predefined_queries = [
        {
            "name": "Find Customer Orders (Unoptimized)",
            "query": "SELECT * FROM orders WHERE customer_id = 101"
        },
        {
            "name": "Heavy JOIN (All Order Items with Product and Customer details)",
            "query": "SELECT c.name, p.name, oi.quantity, oi.price FROM customers c JOIN orders o ON c.id = o.customer_id JOIN order_items oi ON o.id = oi.order_id JOIN products p ON oi.product_id = p.id"
        },
        {
            "name": "Filter and Sort (Requires Index)",
            "query": "SELECT * FROM products WHERE category = 'Electronics' ORDER BY price DESC"
        }
    ]

    return render_template('analyser.html', predefined_queries=predefined_queries)

@analyser_bp.route('/api/analyse-query', methods=['POST'])
def analyse_query_api():
    if not session.get('user_id'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
        
    data = request.get_json()
    query = data.get('query')
    
    if not query:
        return jsonify({"success": False, "error": "Query is required"}), 400
        
    result = QueryAnalyserService.analyze_query(query)
    
    return jsonify(result)
