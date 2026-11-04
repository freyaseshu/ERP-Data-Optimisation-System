"""ERP assessment -> review -> approved action -> verification, with durable evidence."""
import copy
from datetime import date, timedelta
from sqlalchemy import inspect, select, text
from utils.db import db
from utils.query_safety import ERP_TABLES
from utils.time import utc_now
from models.optimization_run import OptimizationRun
from models.performance_log import PerformanceLog
from models.archive_log import ArchiveLog
from services.benchmark_service import BenchmarkService
from services.query_analyser import QueryAnalyserService
from services.query_optimizer import QueryOptimizerService
from services.erp_workload_service import run_mixed_workload


PROFILES = {
    'mixed': 'Concurrent order updates with financial and inventory reporting',
    'transactional': 'Customer order lookups and frequent order / stock updates',
    'financial': 'Revenue aggregation and date-bounded financial reporting',
    'inventory': 'Stock availability, replenishment and inventory reporting',
}
ORDER_LOOKUP = 'SELECT id, customer_id, order_date, status, total_amount FROM orders WHERE customer_id = 101 ORDER BY id'
FINANCIAL = 'SELECT status, count(*) AS orders, sum(total_amount) AS revenue FROM orders GROUP BY status'
INVENTORY = 'SELECT warehouse_location, count(*) AS positions, sum(quantity_on_hand) AS stock FROM inventory GROUP BY warehouse_location'
INDEX_SQL = 'CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders (customer_id);'
ARCHIVE_SQL = ('INSERT INTO public.orders_archive (original_order_id, customer_id, order_date, total_amount, status, archived_at) '
               'SELECT id, customer_id, order_date, total_amount, status, CURRENT_TIMESTAMP FROM public.orders WHERE order_date < :cutoff '
               'ON CONFLICT (original_order_id) DO NOTHING RETURNING original_order_id')


def partition_setup(months):
    if len(months) > 120:
        raise ValueError('Partition experiment is limited to 120 observed months. Use a smaller test database.')
    statements = ['CREATE TEMP TABLE erp_heap_orders (LIKE public.orders) ON COMMIT DROP',
                  'CREATE TEMP TABLE erp_partition_orders (LIKE public.orders) PARTITION BY RANGE (order_date) ON COMMIT DROP']
    for month in months:
        end = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
        statements.append(f"CREATE TEMP TABLE erp_month_{month:%Y%m} PARTITION OF pg_temp.erp_partition_orders FOR VALUES FROM ('{month.isoformat()}') TO ('{end.isoformat()}')")
    statements.append('CREATE TEMP TABLE erp_month_default PARTITION OF pg_temp.erp_partition_orders DEFAULT')
    return statements


def configuration(data):
    if set(data) - {'profile', 'report_date', 'archive_before', 'workers', 'writers', 'operations', 'iterations', 'seed'}:
        raise ValueError('Unknown workspace configuration field.')
    profile = data.get('profile', 'mixed')
    if not isinstance(profile, str) or profile not in PROFILES:
        raise ValueError('Choose mixed, transactional, financial or inventory.')
    values = {'profile': profile}
    for key, default in (('report_date', '2025-01-01'), ('archive_before', '2025-01-01')):
        try:
            value = date.fromisoformat(data.get(key, default))
            if not 2000 <= value.year <= 2099:
                raise ValueError()
            values[key] = value.isoformat()
        except (ValueError, TypeError):
            raise ValueError(key + ' must be an ISO date between 2000 and 2099.') from None
    for key, default, low, high in (('workers', 4, 2, 8), ('writers', 1, 1, 7),
                                    ('operations', 8, 2, 30), ('iterations', 3, 1, 10), ('seed', 42, 0, 2147483647)):
        value = data.get(key, default)
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f'{key} must be an integer from {low} to {high}.')
        values[key] = value
    if values['writers'] >= values['workers']:
        raise ValueError('Keep at least one reporting worker alongside the UPDATE workers.')
    return values


def date_queries(config):
    day = date.fromisoformat(config['report_date'])
    end = day + timedelta(days=1)
    projection = 'SELECT id, customer_id, order_date, total_amount, status FROM orders WHERE '
    return (projection + f"order_date::date = DATE '{day.isoformat()}' ORDER BY id",
            projection + f"order_date >= TIMESTAMP '{day.isoformat()}' AND order_date < TIMESTAMP '{end.isoformat()}' ORDER BY id")


def action(key, kind, title, sql, rationale, risks, scope):
    return {'id': key, 'kind': kind, 'title': title, 'status': 'Pending', 'sql': sql,
            'rationale': rationale, 'risks': risks, 'scope': scope, 'decisions': [], 'result': None}


def assess(data, actor):
    config = configuration(data)
    original, rewritten = date_queries(config)
    queries = [('Order lookup', ORDER_LOOKUP), ('Financial reporting', FINANCIAL), ('Inventory reporting', INVENTORY), ('Date predicate', original)]
    if config['profile'] == 'financial':
        queries = [queries[1], queries[3], queries[0], queries[2]]
    elif config['profile'] == 'inventory':
        queries = [queries[2], queries[0], queries[1], queries[3]]
    evidence = []
    for name, sql in queries:
        analysis = QueryAnalyserService.analyze_query(sql, run_analyze=True, record=False)
        if not analysis['success']:
            raise ValueError(analysis['error'])
        evidence.append({'name': name, 'sql': sql, **analysis})
    with db.engine.connect() as conn:
        counts = {table: conn.exec_driver_sql('SELECT count(*) FROM public.' + table).scalar() for table in ERP_TABLES}
        activity = [dict(row) for row in conn.execute(text(
            'SELECT relname, seq_scan, idx_scan, n_tup_ins, n_tup_upd, n_tup_del, n_live_tup '
            "FROM pg_stat_user_tables WHERE schemaname='public' AND relname IN ('orders','inventory','payments','transactions') ORDER BY relname")).mappings()]
        indexes = inspect(conn).get_indexes('orders', schema='public')
        months = list(conn.exec_driver_sql("SELECT DISTINCT date_trunc('month', order_date)::date FROM public.orders WHERE order_date IS NOT NULL ORDER BY 1").scalars())
        archive_count = conn.execute(text('SELECT count(*) FROM public.orders o WHERE order_date < :cutoff AND NOT EXISTS '
            '(SELECT 1 FROM public.orders_archive a WHERE a.original_order_id=o.id)'), {'cutoff': date.fromisoformat(config['archive_before'])}).scalar()
    actions = [
        action('index-orders', 'INDEX', 'Tune customer order lookup', INDEX_SQL,
               'Review the order lookup plan and its filter. Benchmark a customer_id index only if no full leading-column index already covers it.',
               'Index creation briefly blocks writes, consumes storage and adds UPDATE/INSERT cost. The planner may retain a sequential scan.', 'Approved live index; transactional read verification'),
        action('rewrite-date', 'REWRITE', 'Make the financial date predicate indexable', rewritten,
               'Compare a timestamp-to-date cast with a half-open timestamp range for the selected reporting day. Both return the same columns and ordered IDs.',
               'Only this built-in timestamp-without-time-zone ERP query is rewritten. A rewrite can be neutral or slower; inspect measured plans.', 'Verified query alternative; application SQL is not replaced automatically'),
        action('partition-orders', 'PARTITION', 'Test monthly order partitions',
               ';\n'.join(partition_setup(months)) + ';\n' + '\n'.join(
                   f'INSERT INTO pg_temp.{table} SELECT * FROM public.orders;\nCREATE INDEX ON pg_temp.{table} (order_date);\nANALYZE pg_temp.{table};'
                   for table in ('erp_heap_orders', 'erp_partition_orders')),
               'Compare an ordinary heap with monthly range partitions on identical order copies. Retain pruning evidence and full copy equivalence.',
               'Copies consume temporary disk and setup time. Production conversion needs primary-key / foreign-key migration and retention planning.', 'Temporary partition experiment; no live table conversion'),
        action('archive-orders', 'ARCHIVE', 'Snapshot historical orders',
               ARCHIVE_SQL + ';\n-- :cutoff = ' + config['archive_before'],
               f"Preview: {archive_count} order headers before {config['archive_before']} have no snapshot. Recalculate at execution and verify each newly copied row.",
               'This preserves live orders and relationships. Header snapshots exclude items/payments and do not reclaim live storage.', 'Approved persistent order-header snapshots'),
        action('mixed-workload', 'WORKLOAD', 'Compare reporting and transactional UPDATE cost',
               'Sandbox candidates: orders(customer_id), orders(status, order_date). All UPDATE transactions roll back.',
               f"Replay identical seeded order lookups, financial/inventory reports and stock/order updates using {config['workers']} workers ({config['writers']} writers).",
               'Synthetic local concurrency; includes rollback cost but excludes commit latency. Candidate indexes may add write overhead or duplicate existing indexes.', 'Disposable copies; bounded concurrent operations'),
    ]
    assessment = {'profile_description': PROFILES[config['profile']], 'queries': evidence, 'dataset_counts': counts,
                  'database_activity': activity, 'activity_note': 'Cumulative PostgreSQL counters since statistics reset; not a sampled traffic rate or an inferred production workload.',
                  'existing_order_indexes': indexes, 'archive_preview_count': archive_count,
                  'environment': BenchmarkService.get_environment_info(),
                  'workflow': 'Assess ERP workload -> review evidence and trade-offs -> administrator approves each action -> verify results -> export evidence'}
    # SQLAlchemy inspector dictionaries may contain dialect objects; store plain JSON.
    import json
    assessment = json.loads(json.dumps(assessment, default=str))
    run = OptimizationRun(created_by=actor, profile=config['profile'], configuration=config, assessment=assessment, actions=actions)
    db.session.add(run)
    db.session.commit()
    return run.to_dict()


def compare(conn, before_sql, after_sql, iterations, change=None, trusted=False):
    sampler = QueryOptimizerService._sample_trusted if trusted else QueryOptimizerService.sample
    before = sampler(conn, before_sql, iterations)
    if change:
        change()
    after = sampler(conn, after_sql, iterations)
    equivalent = before['fingerprint'] == after['fingerprint'] and before['columns'] == after['columns']
    if not equivalent:
        raise ValueError('Result equivalence failed; the entire action was rolled back.')
    gain = (before['mean_ms'] - after['mean_ms']) / before['mean_ms'] * 100 if before['mean_ms'] > 0 else None
    return {'equivalent': True, 'baseline_time_ms': before['mean_ms'], 'optimised_time_ms': after['mean_ms'],
            'improvement_percentage': gain, 'baseline_samples_ms': before['samples_ms'], 'optimised_samples_ms': after['samples_ms'],
            'baseline_stddev_ms': before['stddev_ms'], 'optimised_stddev_ms': after['stddev_ms'],
            'baseline_plan': before['plan'], 'optimised_plan': after['plan'], 'rows_returned': after['rows'],
            'baseline_sql': before_sql, 'optimised_sql': after_sql,
            'controls': 'Same repeatable-read snapshot, SHARE locks on ERP data, one excluded warm-up per side; PostgreSQL server execution time. Full SHA-256 row multisets including duplicate counts and column names are checked separately; row order is ignored.'}


def partition_experiment(conn, config):
    months = list(conn.exec_driver_sql("SELECT DISTINCT date_trunc('month', order_date)::date FROM public.orders WHERE order_date IS NOT NULL ORDER BY 1").scalars())
    statements = partition_setup(months)
    for sql in statements:
        conn.exec_driver_sql(sql)
    for table in ('erp_heap_orders', 'erp_partition_orders'):
        conn.exec_driver_sql(f'INSERT INTO pg_temp.{table} SELECT * FROM public.orders')
        conn.exec_driver_sql(f'CREATE INDEX ON pg_temp.{table} (order_date)')
        conn.exec_driver_sql(f'ANALYZE pg_temp.{table}')
    # Verify the entire copied dataset, not only one date's report.
    source = QueryOptimizerService._sample_trusted(conn, 'SELECT * FROM public.orders', 1)
    partitioned = QueryOptimizerService._sample_trusted(conn, 'SELECT * FROM pg_temp.erp_partition_orders', 1)
    heap = QueryOptimizerService._sample_trusted(conn, 'SELECT * FROM pg_temp.erp_heap_orders', 1)
    if not source['fingerprint'] == partitioned['fingerprint'] == heap['fingerprint']:
        raise ValueError('Partition copies differ from the live source snapshot.')
    _, report = date_queries(config)
    result = compare(conn, report.replace('FROM orders', 'FROM pg_temp.erp_heap_orders'),
                     report.replace('FROM orders', 'FROM pg_temp.erp_partition_orders'), config['iterations'], trusted=True)
    scanned = []
    def visit(node):
        if node.get('Relation Name'):
            scanned.append(node['Relation Name'])
        for child in node.get('Plans', []):
            visit(child)
    visit(result['optimised_plan']['Plan'])
    result.update(partitions=len(months) + 1, partitions_scanned=sorted(set(scanned)),
                  full_copy_equivalent=True, source_rows=source['rows'], sandbox_removed_on_commit=True,
                  setup_sql=statements, comparable_indexes='Both copies have the same order_date B-tree index and fresh ANALYZE statistics.',
                  note='Temporary-copy comparison excludes copy/index build costs from query timings. All copies disappear at transaction end. Live primary keys and foreign keys are not migrated.')
    return result


def archive_verified(conn, config, actor):
    before = QueryOptimizerService.sample(conn, 'SELECT * FROM orders', 1)
    rows = list(conn.execute(text(ARCHIVE_SQL),
        {'cutoff': date.fromisoformat(config['archive_before'])}).scalars())
    mismatches = conn.execute(text('SELECT count(*) FROM public.orders_archive a JOIN public.orders o ON a.original_order_id=o.id '
        'WHERE a.original_order_id = ANY(:ids) AND (a.customer_id, a.order_date, a.total_amount, a.status) '
        'IS DISTINCT FROM (o.customer_id, o.order_date, o.total_amount, o.status)'), {'ids': rows}).scalar()
    after = QueryOptimizerService.sample(conn, 'SELECT * FROM orders', 1)
    if mismatches or before['fingerprint'] != after['fingerprint']:
        raise ValueError('Archive verification failed; snapshots were rolled back.')
    conn.execute(ArchiveLog.__table__.insert().values(table_name='orders', records_archived=len(rows), archived_by=actor))
    return {'equivalent': True, 'records_archived': len(rows), 'new_snapshot_values_verified': True,
            'live_orders_unchanged': True, 'live_order_count': after['rows'],
            'note': 'Verified new header snapshots. Previously archived headers remain point-in-time snapshots. No live rows deleted; no space reclamation or query speedup is claimed.'}


def execute(conn, key, config, actor):
    if not conn.exec_driver_sql('SELECT pg_try_advisory_xact_lock(620432)').scalar():
        raise ValueError('Another benchmark is running; retry when it finishes.')
    if key == 'mixed-workload':
        return run_mixed_workload(db.engine, config)
    conn.exec_driver_sql('LOCK TABLE ' + ', '.join('public.' + t for t in ERP_TABLES) + ' IN SHARE MODE')
    if key == 'index-orders':
        indexes = inspect(conn).get_indexes('orders', schema='public')
        present = any(i['column_names'] and i['column_names'][0] == 'customer_id' and not i.get('dialect_options', {}).get('postgresql_where') for i in indexes)
        named = conn.exec_driver_sql("SELECT to_regclass('public.idx_orders_customer_id')").scalar()
        if named and not any(i['name'] == 'idx_orders_customer_id' and i['column_names'] == ['customer_id'] and not i.get('dialect_options', {}).get('postgresql_where') for i in indexes):
            raise ValueError('Candidate index name is already used by another definition.')
        result = compare(conn, ORDER_LOOKUP, ORDER_LOOKUP, config['iterations'],
                         None if present else lambda: conn.exec_driver_sql(INDEX_SQL.replace('ON orders', 'ON public.orders')))
        result.update(index_created=not present, index_already_present=present,
                      index_size_bytes=conn.exec_driver_sql("SELECT pg_relation_size('public.idx_orders_customer_id'::regclass)").scalar() if not present else None,
                      note='Existing leading-column index retained; no new optimization attribution.' if present else 'New live index. Check the mixed workload comparison for write trade-offs.')
        return result
    if key == 'rewrite-date':
        original, rewritten = date_queries(config)
        return compare(conn, original, rewritten, config['iterations'])
    if key == 'partition-orders':
        return partition_experiment(conn, config)
    if key == 'archive-orders':
        return archive_verified(conn, config, actor)
    raise ValueError('Unknown action.')


def decide(run_id, key, decision, actor):
    if decision not in ('approve', 'reject'):
        raise ValueError('Choose approve or reject.')
    table = OptimizationRun.__table__
    # All execution and the corresponding decision/evidence commit atomically.
    operation_started = False
    try:
        with db.engine.begin() as conn:
            conn.exec_driver_sql('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            conn.exec_driver_sql("SET LOCAL lock_timeout = '2s'")
            conn.exec_driver_sql("SET LOCAL statement_timeout = '30s'")
            row = conn.execute(select(table).where(table.c.id == run_id).with_for_update()).mappings().one_or_none()
            if row is None:
                raise ValueError('Workspace run not found.')
            actions = copy.deepcopy(row['actions'])
            selected = next((item for item in actions if item['id'] == key), None)
            if selected is None or selected['status'] not in ('Pending', 'Failed'):
                raise ValueError('Choose a pending or failed action.')
            event = {'decision': decision, 'actor': actor, 'at': utc_now().isoformat() + 'Z'}
            if decision == 'reject':
                selected['status'] = 'Rejected'
            else:
                operation_started = True
                result = execute(conn, key, row['configuration'], actor)
                selected.update(status='Applied' if key in ('index-orders', 'archive-orders') else 'Verified', result=result)
                log = conn.execute(PerformanceLog.__table__.insert().values(query_name=selected['title'], query_text=selected['sql'],
                    execution_time_before=result.get('baseline_time_ms'), execution_time_after=result.get('optimised_time_ms'),
                    improvement_percentage=result.get('improvement_percentage'),
                    optimization_applied=INDEX_SQL if key == 'index-orders' and result.get('index_created') else None,
                    status='Workspace verified', details={'workspace_run_id': run_id, 'action_id': key, 'actor': actor, **result}).returning(PerformanceLog.id)).scalar_one()
                selected['performance_log_id'] = log
            selected['decisions'].append(event)
            selected.pop('error', None)
            conn.execute(table.update().where(table.c.id == run_id).values(actions=actions))
        return {'success': True, 'action': selected}
    except Exception as exc:
        if operation_started:
            error = str(exc) if isinstance(exc, ValueError) else 'Action failed and was rolled back. Check PostgreSQL, schema, locks, disk space and timeouts.'
            with db.engine.begin() as conn:
                conn.exec_driver_sql("SET LOCAL lock_timeout = '2s'")
                row = conn.execute(select(table).where(table.c.id == run_id).with_for_update()).mappings().one()
                actions = copy.deepcopy(row['actions'])
                selected = next(item for item in actions if item['id'] == key)
                if selected['status'] in ('Pending', 'Failed'):
                    selected.update(status='Failed', error=error)
                    selected['decisions'].append({'decision': 'approve', 'actor': actor, 'at': utc_now().isoformat() + 'Z', 'error': error})
                    conn.execute(table.update().where(table.c.id == run_id).values(actions=actions))
            return {'success': False, 'error': error}
        raise
