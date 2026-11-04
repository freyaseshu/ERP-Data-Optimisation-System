"""Bounded concurrent reporting/UPDATE comparisons on disposable ERP copies.

Every UPDATE is rolled back. No live table is modified. Both phases replay the
same seeded operation lists. Latencies include SQL execution and rollback, but
exclude connection checkout. This is a local experiment, not a capacity claim.
"""
import hashlib
import json
import math
import random
import re
import statistics
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import text


def summarize(samples):
    ordered = sorted(samples)
    return {'count': len(samples), 'mean_ms': statistics.mean(samples),
            'p50_ms': statistics.median(samples),
            'p95_ms': ordered[max(0, math.ceil(len(ordered) * .95) - 1)],
            'stddev_ms': statistics.pstdev(samples), 'samples_ms': samples}


def fingerprint(conn, schema):
    digest = hashlib.sha256()
    for table in ('orders', 'inventory'):
        for row in conn.exec_driver_sql(f'SELECT * FROM {schema}.{table} ORDER BY id'):
            digest.update(json.dumps(list(row), default=str).encode())
            digest.update(b'\n')
    return digest.hexdigest()


def result_fingerprint(rows):
    # Sort encoded rows to ignore plan-dependent order while retaining duplicates.
    encoded = sorted(json.dumps(list(row), default=str) for row in rows)
    return hashlib.sha256(json.dumps(encoded).encode()).hexdigest()


def run_mixed_workload(engine, configuration):
    schema = 'erp_bench_' + uuid.uuid4().hex
    # Identifier is generated here; never read from an API or stored action.
    assert re.fullmatch(r'erp_bench_[0-9a-f]{32}', schema)
    workers, writers = configuration['workers'], configuration['writers']
    operations, seed = configuration['operations'], configuration['seed']
    created = False
    result = None
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("SET LOCAL statement_timeout = '30s'")
            conn.exec_driver_sql("SET LOCAL lock_timeout = '2s'")
            conn.exec_driver_sql('LOCK TABLE public.orders, public.inventory IN SHARE MODE')
            conn.exec_driver_sql('CREATE SCHEMA ' + schema)
            created = True
            for table in ('orders', 'inventory'):
                conn.exec_driver_sql(f'CREATE TABLE {schema}.{table} (LIKE public.{table} INCLUDING ALL)')
                conn.exec_driver_sql(f'INSERT INTO {schema}.{table} SELECT * FROM public.{table}')
                conn.exec_driver_sql(f'ANALYZE {schema}.{table}')
            order_ids = list(conn.exec_driver_sql(f'SELECT id FROM {schema}.orders ORDER BY id').scalars())
            inventory_ids = list(conn.exec_driver_sql(f'SELECT id FROM {schema}.inventory ORDER BY id').scalars())
            customer_ids = list(conn.exec_driver_sql(f'SELECT DISTINCT customer_id FROM {schema}.orders ORDER BY customer_id').scalars())
            if not order_ids or not inventory_ids:
                raise ValueError('Orders and inventory must contain records for a mixed ERP experiment.')
            original = fingerprint(conn, schema)
            existing_indexes = [dict(r) for r in conn.execute(text(
                'SELECT tablename, indexdef FROM pg_indexes WHERE schemaname=:schema ORDER BY indexname'),
                {'schema': schema}).mappings()]

        # Precompute the exact operation stream; both phases use it unchanged.
        streams = []
        mix = {
            'mixed': ('order_lookup', 'financial_report', 'inventory_report'),
            'transactional': ('order_lookup', 'order_lookup', 'order_lookup', 'financial_report', 'inventory_report'),
            'financial': ('financial_report', 'financial_report', 'order_lookup', 'inventory_report'),
            'inventory': ('inventory_report', 'inventory_report', 'order_lookup', 'financial_report'),
        }[configuration['profile']]
        for worker in range(workers):
            rng = random.Random(seed + worker)
            streams.append([(i % 2, mix[(i + worker) % len(mix)], rng.choice(order_ids), rng.choice(inventory_ids), rng.choice(customer_ids))
                            for i in range(operations)])

        def phase():
            barrier = threading.Barrier(workers, timeout=15)
            def task(worker):
                samples = {'transactional_update': [], 'financial_report': [], 'inventory_report': [], 'order_lookup': []}
                results = []
                with engine.connect() as conn:
                    # Same excluded warm-up for each worker in each phase.
                    with conn.begin():
                        conn.exec_driver_sql("SET LOCAL statement_timeout = '5s'")
                        conn.exec_driver_sql(f'SELECT count(*) FROM {schema}.orders').scalar()
                    barrier.wait()
                    for kind, read_kind, order_id, inventory_id, customer_id in streams[worker]:
                        transaction = conn.begin()
                        try:
                            conn.exec_driver_sql("SET LOCAL statement_timeout = '5s'")
                            conn.exec_driver_sql("SET LOCAL lock_timeout = '1s'")
                            start = time.perf_counter()
                            rows = None
                            if worker < writers:
                                label = 'transactional_update'
                                if kind == 0:
                                    updated = conn.execute(text(f'UPDATE {schema}.inventory SET quantity_on_hand=quantity_on_hand+1 WHERE id=:id'), {'id': inventory_id})
                                else:
                                    updated = conn.execute(text(f"UPDATE {schema}.orders SET status='Processing' WHERE id=:id"), {'id': order_id})
                                if updated.rowcount != 1:
                                    raise ValueError('Expected exactly one sandbox ERP row to be updated.')
                            elif read_kind == 'order_lookup':
                                label = 'order_lookup'
                                rows = conn.execute(text(f'SELECT id, status, total_amount FROM {schema}.orders WHERE customer_id=:id ORDER BY id'), {'id': customer_id}).fetchall()
                            elif read_kind == 'financial_report':
                                label = 'financial_report'
                                rows = conn.exec_driver_sql(f'SELECT status, count(*), sum(total_amount) FROM {schema}.orders GROUP BY status').fetchall()
                            else:
                                label = 'inventory_report'
                                rows = conn.exec_driver_sql(f'SELECT warehouse_location, sum(quantity_on_hand) FROM {schema}.inventory GROUP BY warehouse_location').fetchall()
                        finally:
                            transaction.rollback()
                        samples[label].append((time.perf_counter() - start) * 1000)
                        if rows is not None:
                            results.append(result_fingerprint(rows))
                return {'samples': samples, 'result_fingerprints': results}
            start = time.perf_counter()
            with ThreadPoolExecutor(max_workers=workers) as executor:
                batches = list(executor.map(task, range(workers)))
            elapsed = time.perf_counter() - start
            samples = {key: [s for batch in batches for s in batch['samples'][key]] for key in batches[0]['samples']}
            return {'duration_seconds': elapsed, 'operations': workers * operations,
                    'throughput_ops_per_second': workers * operations / elapsed,
                    'metrics': {key: summarize(values) for key, values in samples.items() if values}, 'errors': 0,
                    'result_fingerprints_by_worker': [batch['result_fingerprints'] for batch in batches]}

        baseline = phase()
        with engine.begin() as conn:
            if fingerprint(conn, schema) != original:
                raise ValueError('Baseline sandbox data changed unexpectedly.')
            # Fixed, reviewed candidates. Keep copied existing indexes on both sides.
            conn.exec_driver_sql(f'CREATE INDEX erp_candidate_customer ON {schema}.orders (customer_id)')
            conn.exec_driver_sql(f'CREATE INDEX erp_candidate_status_date ON {schema}.orders (status, order_date)')
        after = phase()
        with engine.connect() as conn:
            equivalent = fingerprint(conn, schema) == original
        reports_equivalent = baseline['result_fingerprints_by_worker'] == after['result_fingerprints_by_worker']
        if not equivalent or not reports_equivalent:
            raise ValueError('Sandbox data or per-operation report results changed across phases.')
        result = {'success': True, 'baseline': baseline, 'after': after, 'equivalent': equivalent,
                  'configuration': configuration, 'copied_existing_indexes': existing_indexes,
                  'all_read_results_equivalent': reports_equivalent, 'source_data_fingerprint': original,
                  'candidates': ['orders(customer_id)', 'orders(status, order_date)'],
                  'scope': 'Isolated copies of orders and inventory; all UPDATE transactions roll back. No commit latency, live ERP writes, or production capacity measurement.',
                  'controls': 'Identical seeded operations, data, workers and warm-ups; existing indexes copied to both phases. Wall time includes worker startup and result hashing; per-operation latency excludes pool checkout and result hashing. Full per-operation row multisets and final copied data are verified.',
                  'note': 'Additional indexes may duplicate copied indexes. Compare read gains and UPDATE overhead; improvements are not guaranteed.'}
    finally:
        if created:
            with engine.begin() as conn:
                conn.exec_driver_sql("SET LOCAL lock_timeout = '2s'")
                conn.exec_driver_sql('DROP SCHEMA IF EXISTS ' + schema + ' CASCADE')
    result['sandbox_removed'] = True
    return result
