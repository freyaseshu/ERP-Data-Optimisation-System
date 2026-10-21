from utils.time import utc_now
import csv
import io
from datetime import datetime, timedelta
from sqlalchemy import func
from models.performance_log import PerformanceLog
from models.optimisation_recommendation import OptimisationRecommendation
from models.archive_log import ArchiveLog
from utils.db import db

def get_performance_report(range_key='30days', start=None, end=None):
    query = PerformanceLog.query
    now = utc_now()
    if range_key in ('today', '7days', '30days'):
        since = now.replace(hour=0, minute=0, second=0, microsecond=0) if range_key == 'today' else now - timedelta(days=7 if range_key == '7days' else 30)
        query = query.filter(PerformanceLog.created_at >= since)
    elif range_key == 'custom':
        try:
            first, last = datetime.fromisoformat(start), datetime.fromisoformat(end) + timedelta(days=1)
        except (TypeError, ValueError):
            raise ValueError('Custom range requires valid start and end dates.') from None
        if first >= last:
            raise ValueError('Start must be on or before end.')
        query = query.filter(PerformanceLog.created_at >= first, PerformanceLog.created_at < last)
    elif range_key != 'all':
        raise ValueError('Unknown report range.')
    logs = query.order_by(PerformanceLog.created_at.desc()).all()
    rows = [l.to_dict() for l in logs]
    after = [r['execution_time_after'] for r in rows if r['execution_time_after'] is not None]
    gains = [r['improvement_percentage'] for r in rows if r['improvement_percentage'] is not None]
    from services.duplicate_checker import find_duplicates, TABLE_CONFIG
    duplicates = sum(find_duplicates(t)['total_duplicate_records'] for t in TABLE_CONFIG)
    return {'slowest_queries': sorted([r for r in rows if r['execution_time_before'] is not None], key=lambda r: r['execution_time_before'], reverse=True)[:10],
            'fastest_queries': sorted([r for r in rows if r['execution_time_after'] is not None], key=lambda r: r['execution_time_after'])[:10],
            'average_execution_time_ms': round(sum(after) / len(after), 3) if after else None,
            'average_improvement_percentage': round(sum(gains) / len(gains), 2) if gains else None,
            'queries_optimized': sum(bool(r['optimization_applied']) for r in rows),
            'indexes_suggested': OptimisationRecommendation.query.filter_by(recommendation_type='INDEX').count(),
            'duplicate_records_found': duplicates,
            'records_archived': db.session.query(func.coalesce(func.sum(ArchiveLog.records_archived), 0)).scalar(),
            'all_logs': rows, 'generated_at': now.isoformat() + 'Z', 'range': range_key}

def export_report_csv(range_key='30days', start=None, end=None):
    report = get_performance_report(range_key, start, end)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Log ID', 'Query', 'Before (ms)', 'After (ms)', 'Optimisation Applied', 'Improvement %', 'Timestamp (UTC)', 'Status', 'Evidence JSON'])
    import json
    for row in report['all_logs']:
        values = [row['id'], row['query_text'], row['execution_time_before'], row['execution_time_after'], row['optimization_applied'], row['improvement_percentage'], row['created_at'], row['status'], json.dumps(row['details'], default=str)]
        writer.writerow(["'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@', '\t', '\r')) else v for v in values])
    return output.getvalue()
