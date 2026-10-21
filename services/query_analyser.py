from flask import current_app
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from utils.query_safety import validate, readonly_connection
from models.performance_log import PerformanceLog
from utils.db import db

class QueryAnalyserService:
    @staticmethod
    def is_safe_query(query):
        try:
            validate(query)
            return True, 'Safe read-only query.'
        except ValueError as exc:
            return False, str(exc)

    @staticmethod
    def analyze_query(query, run_analyze=False, record=True):
        try:
            sql = validate(query)
            with readonly_connection() as conn:
                prefix = 'EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ' if run_analyze else 'EXPLAIN (FORMAT JSON) '
                document = conn.exec_driver_sql(prefix + sql).scalar_one()[0]
            plan = []
            warnings = []
            def visit(node, depth=0):
                plan.append({'node_type': node['Node Type'], 'table': node.get('Relation Name'), 'alias': node.get('Alias'),
                             'estimated_rows': node.get('Plan Rows'), 'actual_rows': node.get('Actual Rows'),
                             'total_cost': node.get('Total Cost'), 'actual_time_ms': node.get('Actual Total Time'),
                             'index': node.get('Index Name'), 'filter': node.get('Filter') or node.get('Index Cond'), 'depth': depth})
                removed = node.get('Rows Removed by Filter', 0)
                if node['Node Type'] == 'Seq Scan' and removed > max(1000, node.get('Actual Rows', 0) * 4):
                    warnings.append('Selective filter on ' + node.get('Relation Name', 'table') + ': many rows were discarded. Consider an index after checking selectivity and write overhead.')
                if node.get('Sort Space Type') == 'Disk':
                    warnings.append('Sort spilled to disk; review sort columns, indexes and work_mem.')
                for child in node.get('Plans', []):
                    visit(child, depth + 1)
            visit(document['Plan'])
            execution = document.get('Execution Time')
            if record and run_analyze:
                db.session.add(PerformanceLog(query_text=sql, execution_time_before=execution, status='Analysed', details={'plan': document}))
                db.session.commit()
            return {'success': True, 'plan': plan, 'raw_plan': document, 'warnings': warnings,
                    'original_query': sql, 'measurement': 'actual' if run_analyze else 'estimated',
                    'planning_time_ms': document.get('Planning Time'), 'execution_time_ms': execution,
                    'returned_rows': document['Plan'].get('Actual Rows')}
        except ValueError as exc:
            return {'success': False, 'error': str(exc)}
        except SQLAlchemyError as exc:
            db.session.rollback()
            orig = getattr(exc, 'orig', None)
            message = getattr(getattr(orig, 'diag', None), 'message_primary', None)
            return {'success': False, 'error': message or 'PostgreSQL unavailable; check the connection and schema.'}

    @staticmethod
    def execute_query(query):
        try:
            sql = validate(query)
            limit = current_app.config['QUERY_RESULT_LIMIT']
            with readonly_connection() as conn:
                result = conn.exec_driver_sql('SELECT * FROM (' + sql + ') AS approved_query LIMIT ' + str(limit + 1))
                columns = list(result.keys())
                rows = [list(row) for row in result]
            return {'success': True, 'columns': columns, 'rows': rows[:limit], 'returned_rows': min(len(rows), limit), 'truncated': len(rows) > limit, 'limit': limit}
        except ValueError as exc:
            return {'success': False, 'error': str(exc)}
        except SQLAlchemyError as exc:
            orig = getattr(exc, 'orig', None)
            return {'success': False, 'error': getattr(getattr(orig, 'diag', None), 'message_primary', None) or 'Query execution failed.'}
