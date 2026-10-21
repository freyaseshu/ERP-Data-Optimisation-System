from utils.time import utc_now
import re
import time
import statistics
import hashlib
import json
from collections import Counter
from datetime import datetime
from sqlalchemy import inspect, text
from utils.db import db
from utils.query_safety import validate, readonly_connection, ERP_TABLES
from models.optimisation_recommendation import OptimisationRecommendation
from services.query_analyser import QueryAnalyserService

class QueryOptimizerService:
    @staticmethod
    def sample(conn, query, runs=3):
        sql = validate(query)
        if type(runs) is not int or not 1 <= runs <= 10:
            raise ValueError('iterations must be an integer from 1 to 10.')
        prefix = 'EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) '
        conn.exec_driver_sql(prefix + sql).scalar_one()  # warm-up excluded
        documents = [conn.exec_driver_sql(prefix + sql).scalar_one()[0] for _ in range(runs)]
        timings = [doc['Execution Time'] for doc in documents]
        digest = Counter()
        rows = 0
        with conn.execution_options(stream_results=True).exec_driver_sql(sql) as result:
            for row in result:
                digest[hashlib.sha256(json.dumps(list(row), default=str, ensure_ascii=False).encode()).hexdigest()] += 1
                rows += 1
        conn.execution_options(stream_results=False)
        return {'mean_ms': statistics.mean(timings), 'stddev_ms': statistics.pstdev(timings), 'samples_ms': timings,
                'fingerprint': digest, 'rows': rows, 'plan': documents[-1]}

    @classmethod
    def measure_execution_time(cls, query, runs=3):
        try:
            with readonly_connection() as conn:
                return cls.sample(conn, query, runs)['mean_ms'], None
        except ValueError as exc:
            return None, str(exc)
        except Exception:
            return None, 'Query measurement failed. Check SQL, PostgreSQL connection and timeout.'

    @classmethod
    def verify_query_equivalence(cls, query_a, query_b):
        try:
            with readonly_connection() as conn:
                a = cls.sample(conn, query_a, 1)
                b = cls.sample(conn, query_b, 1)
            return {'equivalent': a['fingerprint'] == b['fingerprint'], 'rows_a': a['rows'], 'rows_b': b['rows'], 'method': 'SHA-256 row multiset including duplicate multiplicity; ignores row order'}
        except Exception:
            return {'equivalent': None, 'error': 'Unable to verify query equivalence.'}

    @classmethod
    def generate_suggestions(cls, query):
        try:
            query = validate(query)
        except ValueError as exc:
            return {'success': False, 'error': str(exc)}
        analysis = QueryAnalyserService.analyze_query(query, run_analyze=True)
        if not analysis['success']:
            return analysis
        suggestions = []
        metadata = inspect(db.engine)
        for node in analysis['plan']:
            table = node.get('table')
            if node['node_type'] != 'Seq Scan' or table not in ERP_TABLES or not node.get('filter'):
                continue
            # PostgreSQL supplies the expression; intersect its identifiers with catalog columns.
            names = {c['name'] for c in metadata.get_columns(table)}
            candidates = [c for c in re.findall(r'\b([a-z_][a-z_0-9]*)\s*(?:=|>|<)', node['filter']) if c in names]
            indexes = metadata.get_indexes(table)
            for column in dict.fromkeys(candidates):
                if any(i['column_names'] and i['column_names'][0] == column and not i.get('dialect_options', {}).get('postgresql_where') for i in indexes):
                    continue
                if column in metadata.get_pk_constraint(table)['constrained_columns']:
                    continue
                ddl = f'CREATE INDEX IF NOT EXISTS idx_{table}_{column} ON {table} ({column});'
                rec = OptimisationRecommendation.query.filter_by(query_text=query.strip(), sql_statement=ddl, status='Pending').first()
                if not rec:
                    rec = OptimisationRecommendation(query_text=query.strip(), recommendation_type='INDEX', title=f'Index {table}.{column}', description='Candidate index from a filtered sequential scan. Sequential scans may still be cheaper for broad filters or small tables. An index uses storage and adds write cost.', sql_statement=ddl)
                    db.session.add(rec)
                    db.session.flush()
                if not any(s.get('id') == rec.id for s in suggestions):
                    suggestions.append({'id': rec.id, 'type': 'index', 'description': rec.description, 'sql': ddl, 'table': table, 'column': column, 'status': rec.status})
        if re.search(r'SELECT\s+\*', query, re.I):
            suggestions.append({'type': 'rewrite', 'description': 'Select only required columns to reduce transfer. Choose columns based on application needs; automatic rewriting is unavailable.', 'sql': None})
        db.session.commit()
        return {'success': True, 'original_query': query, 'proposed_query': None, 'plan': analysis['plan'], 'warnings': analysis['warnings'], 'suggestions': suggestions, 'execution_time_before': analysis['execution_time_ms']}

    @classmethod
    def apply_optimization(cls, optimization_sql=None, original_query=None, recommendation_id=None):
        rec = OptimisationRecommendation.query.filter_by(id=recommendation_id).with_for_update().one_or_none() if recommendation_id else None
        if rec is None or rec.status != 'Pending':
            return {'success': False, 'error': 'Choose a pending server-generated recommendation.'}
        from services.benchmark_service import BenchmarkService
        result = BenchmarkService.run_comparison(rec.query_text, rec.sql_statement, rec.title, 3)
        rec.status = 'Applied' if result.get('success') else 'Unsuccessful'
        rec.applied_at = utc_now() if result.get('success') else None
        db.session.commit()
        return result
