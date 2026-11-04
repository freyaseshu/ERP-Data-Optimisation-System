"""Real PostgreSQL workflow, rollback, approval and ERP workload integration tests."""
import json
import pytest
from sqlalchemy import text
from utils.db import db
from services.optimization_workspace import configuration


@pytest.fixture
def workspace_run(admin_client):
    response = admin_client.post('/api/workspace/runs', json={'iterations': 2, 'workers': 4, 'writers': 1, 'operations': 6})
    assert response.status_code == 201, response.json
    return response.json['run']


def approve(client, run, action):
    return client.post(f"/api/workspace/runs/{run['id']}/actions/{action}", json={'decision': 'approve', 'confirm': True})


def test_workspace_page_and_assessment(admin_client, workspace_run):
    assert admin_client.get('/workspace').status_code == 200
    assert admin_client.get('/api/workspace/runs').json['runs']
    assert admin_client.get(f"/api/workspace/runs/{workspace_run['id']}").json['run'] == workspace_run
    assert workspace_run['assessment']['dataset_counts']['orders'] == 14000
    assert len(workspace_run['assessment']['queries']) == 4
    assert {a['kind'] for a in workspace_run['actions']} == {'INDEX', 'REWRITE', 'PARTITION', 'ARCHIVE', 'WORKLOAD'}
    assert all(a['status'] == 'Pending' and a['rationale'] and a['risks'] for a in workspace_run['actions'])
    assert all(q['raw_plan']['Plan'] and q['execution_time_ms'] >= 0 for q in workspace_run['assessment']['queries'])


@pytest.mark.parametrize('config', [
    {'profile': []}, {'profile': 'unknown'}, {'workers': True}, {'workers': 9}, {'workers': 1},
    {'workers': 2, 'writers': 2}, {'writers': 0}, {'operations': 31}, {'iterations': '3'},
    {'seed': -1}, {'report_date': "2025-01-01'; DROP TABLE orders;--"},
    {'archive_before': None}, {'report_date': '9999-12-31'}, {'sql': 'DROP TABLE orders'}])
def test_invalid_workspace_configuration(config):
    with pytest.raises(ValueError):
        configuration(config)


@pytest.mark.parametrize('profile', ['mixed', 'financial', 'inventory', 'transactional'])
def test_workload_profiles(profile):
    assert configuration({'profile': profile})['profile'] == profile


def test_workspace_requires_authentication(client):
    assert client.get('/workspace').status_code == 302
    for path in ['/api/workspace/runs', '/api/workspace/runs/1', '/api/workspace/runs/1/export']:
        assert client.get(path).status_code == 401
    assert client.post('/api/workspace/runs', json={}).status_code == 401
    assert client.post('/api/workspace/runs/1/actions/index-orders', json={'decision': 'approve', 'confirm': True}).status_code == 401


def test_workspace_analyst_cannot_execute(analyst_client):
    response = analyst_client.post('/api/workspace/runs', json={})
    assert response.status_code == 201
    run = response.json['run']
    assert analyst_client.get(f"/api/workspace/runs/{run['id']}/export").status_code == 200
    for action in run['actions']:
        assert approve(analyst_client, run, action['id']).status_code == 403


def test_explicit_approval_and_server_actions(admin_client, workspace_run):
    path = f"/api/workspace/runs/{workspace_run['id']}/actions/index-orders"
    for data in [{'decision': 'approve'}, {'decision': 'approve', 'confirm': 1},
                 {'decision': 'approve', 'confirm': True, 'sql': 'DROP TABLE orders'}, {'decision': 'arbitrary'}]:
        assert admin_client.post(path, json=data).status_code == 400
    assert approve(admin_client, workspace_run, 'unknown').status_code == 400
    assert admin_client.post(path, json={'decision': 'reject'}).json['success']
    assert approve(admin_client, workspace_run, 'index-orders').status_code == 400
    assert approve(admin_client, {'id': 2147483647}, 'index-orders').status_code == 400


def test_index_verification_and_existing_index_labels(admin_client, workspace_run, app):
    response = approve(admin_client, workspace_run, 'index-orders')
    assert response.status_code == 200, response.json
    action = response.json['action']
    assert action['status'] == 'Applied'
    assert action['result']['equivalent'] is True
    assert action['decisions'][0]['actor'] == 'admin'
    assert action['performance_log_id']
    assert approve(admin_client, workspace_run, 'index-orders').status_code == 400
    with app.app_context():
        assert db.session.execute(text('SELECT details FROM query_performance_logs WHERE id=:id'), {'id': action['performance_log_id']}).scalar()['workspace_run_id'] == workspace_run['id']
    next_run = admin_client.post('/api/workspace/runs', json={}).json['run']
    again = approve(admin_client, next_run, 'index-orders').json['action']['result']
    assert again['index_created'] is False
    assert again['index_already_present'] is True


def test_rewrite_equivalence_includes_empty_day(admin_client, workspace_run):
    response = approve(admin_client, workspace_run, 'rewrite-date')
    assert response.status_code == 200, response.json
    result = response.json['action']['result']
    assert result['equivalent'] is True
    assert len(result['baseline_samples_ms']) == 2
    assert "::date" in result['baseline_sql']
    assert 'TIMESTAMP' in result['optimised_sql']
    empty = admin_client.post('/api/workspace/runs', json={'report_date': '2099-01-01'}).json['run']
    result = approve(admin_client, empty, 'rewrite-date').json['action']['result']
    assert result['equivalent'] is True and result['rows_returned'] == 0


def test_partition_copy_equivalence_pruning_and_cleanup(admin_client, workspace_run, app):
    response = approve(admin_client, workspace_run, 'partition-orders')
    assert response.status_code == 200, response.json
    result = response.json['action']['result']
    assert result['full_copy_equivalent'] and result['equivalent']
    assert result['source_rows'] == 14000
    assert result['partitions'] > len(result['partitions_scanned'])
    assert result['partitions_scanned'] == ['erp_month_202501']
    assert result['baseline_plan']['Plan'] and result['optimised_plan']['Plan']
    with app.app_context(), db.engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT count(*) FROM pg_class WHERE relname IN ('erp_heap_orders','erp_partition_orders','erp_month_default')").scalar() == 0
        assert conn.exec_driver_sql("SELECT relkind FROM pg_class WHERE oid='public.orders'::regclass").scalar() == 'r'


def test_archive_is_verified_idempotent_and_preserves_relationships(admin_client, workspace_run, app):
    with app.app_context(), db.engine.connect() as conn:
        before = {t: conn.exec_driver_sql(f'SELECT count(*) FROM {t}').scalar() for t in ('orders', 'order_items', 'payments', 'transactions')}
    response = approve(admin_client, workspace_run, 'archive-orders')
    assert response.status_code == 200, response.json
    result = response.json['action']['result']
    assert result['equivalent'] and result['live_orders_unchanged'] and result['new_snapshot_values_verified']
    rerun = admin_client.post('/api/workspace/runs', json={}).json['run']
    assert approve(admin_client, rerun, 'archive-orders').json['action']['result']['records_archived'] == 0
    with app.app_context(), db.engine.connect() as conn:
        assert before == {t: conn.exec_driver_sql(f'SELECT count(*) FROM {t}').scalar() for t in before}


def test_mixed_workload_samples_and_cleanup(admin_client, workspace_run, app):
    with app.app_context(), db.engine.connect() as conn:
        from services.erp_workload_service import fingerprint
        before = fingerprint(conn, 'public')
    response = approve(admin_client, workspace_run, 'mixed-workload')
    assert response.status_code == 200, response.json
    result = response.json['action']['result']
    assert result['equivalent'] and result['sandbox_removed']
    assert result['all_read_results_equivalent']
    assert result['baseline']['result_fingerprints_by_worker'] == result['after']['result_fingerprints_by_worker']
    assert result['baseline']['operations'] == result['after']['operations'] == 24
    for phase in ('baseline', 'after'):
        metrics = result[phase]['metrics']
        assert set(metrics) == {'transactional_update', 'order_lookup', 'financial_report', 'inventory_report'}
        assert metrics['transactional_update']['count'] == 6
        assert sum(m['count'] for m in metrics.values()) == 24
        assert all(m['p95_ms'] >= m['p50_ms'] >= 0 for m in metrics.values())
    with app.app_context(), db.engine.connect() as conn:
        assert fingerprint(conn, 'public') == before
        assert conn.execute(text('SELECT count(*) FROM pg_namespace WHERE nspname LIKE :prefix'), {'prefix': 'erp_bench_%'}).scalar() == 0


def test_action_failure_rolls_back_and_can_be_retried(admin_client, workspace_run, app, monkeypatch):
    from services import optimization_workspace as service
    original = service.execute
    def fail_after_write(conn, key, config, actor):
        conn.exec_driver_sql('CREATE INDEX erp_workspace_rollback_probe ON public.employees (salary)')
        conn.exec_driver_sql("INSERT INTO archive_logs (table_name, records_archived, archived_by, archive_date) VALUES ('orders',0,'rollback-test',CURRENT_TIMESTAMP)")
        raise ValueError('Deliberate verification failure')
    monkeypatch.setattr(service, 'execute', fail_after_write)
    response = approve(admin_client, workspace_run, 'index-orders')
    assert response.status_code == 400, response.json
    with app.app_context(), db.engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT to_regclass('public.erp_workspace_rollback_probe')").scalar() is None
        assert conn.exec_driver_sql("SELECT count(*) FROM archive_logs WHERE archived_by='rollback-test'").scalar() == 0
    failed = admin_client.get(f"/api/workspace/runs/{workspace_run['id']}").json['run']['actions'][0]
    assert failed['status'] == 'Failed' and len(failed['decisions']) == 1
    monkeypatch.setattr(service, 'execute', original)
    retried = approve(admin_client, workspace_run, 'index-orders')
    assert retried.status_code == 200, retried.json
    assert len(retried.json['action']['decisions']) == 2


def test_partition_failure_removes_temporary_copies(admin_client, workspace_run, app, monkeypatch):
    from services import optimization_workspace as service
    def mismatch(*args, **kwargs):
        raise ValueError('Injected report equivalence mismatch')
    monkeypatch.setattr(service, 'compare', mismatch)
    response = approve(admin_client, workspace_run, 'partition-orders')
    assert response.status_code == 400, response.json
    with app.app_context(), db.engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT count(*) FROM pg_class WHERE relname IN ('erp_heap_orders','erp_partition_orders','erp_month_default')").scalar() == 0


def test_evidence_export_and_report_link(admin_client, workspace_run):
    assert approve(admin_client, workspace_run, 'rewrite-date').status_code == 200
    exported = admin_client.get(f"/api/workspace/runs/{workspace_run['id']}/export")
    assert exported.status_code == 200 and exported.mimetype == 'application/json'
    run = json.loads(exported.data)
    assert run['actions'][1]['result']['equivalent']
    assert 'attachment' in exported.headers['Content-Disposition']
    csv = admin_client.get('/api/reports/export?range=all')
    assert b'workspace_run_id' in csv.data


def test_profile_changes_report_mix(admin_client):
    run = admin_client.post('/api/workspace/runs', json={'profile': 'financial', 'workers': 2, 'writers': 1, 'operations': 8}).json['run']
    response = approve(admin_client, run, 'mixed-workload')
    assert response.status_code == 200, response.json
    metrics = response.json['action']['result']['baseline']['metrics']
    assert metrics['financial_report']['count'] == 4
    assert metrics['inventory_report']['count'] == 2
    assert metrics['order_lookup']['count'] == 2


def test_maximum_workers_and_write_contention(admin_client):
    run = admin_client.post('/api/workspace/runs', json={'workers': 8, 'writers': 4, 'operations': 6}).json['run']
    response = approve(admin_client, run, 'mixed-workload')
    assert response.status_code == 200, response.json
    result = response.json['action']['result']
    assert result['baseline']['operations'] == result['after']['operations'] == 48
    assert result['baseline']['metrics']['transactional_update']['count'] == 24
    assert result['all_read_results_equivalent'] and result['sandbox_removed']


@pytest.mark.parametrize('mode', ['worker_failure', 'changed_results'])
def test_mixed_failure_cleanup_and_audit(admin_client, workspace_run, app, monkeypatch, mode):
    from services import erp_workload_service as service
    sequence = []
    def injected(rows):
        if mode == 'worker_failure':
            raise RuntimeError('Injected worker failure')
        sequence.append(1)
        return str(len(sequence))
    monkeypatch.setattr(service, 'result_fingerprint', injected)
    response = approve(admin_client, workspace_run, 'mixed-workload')
    assert response.status_code == 400, response.json
    failed = admin_client.get(f"/api/workspace/runs/{workspace_run['id']}").json['run']['actions'][4]
    assert failed['status'] == 'Failed' and failed['decisions'][0]['error']
    with app.app_context(), db.engine.connect() as conn:
        assert conn.execute(text('SELECT count(*) FROM pg_namespace WHERE nspname LIKE :prefix'), {'prefix': 'erp_bench_%'}).scalar() == 0


def test_partition_preserves_null_dates(admin_client, workspace_run, app):
    with app.app_context(), db.engine.begin() as conn:
        original = conn.exec_driver_sql('SELECT id, order_date FROM public.orders ORDER BY id LIMIT 1').one()
        conn.execute(text('UPDATE public.orders SET order_date=NULL WHERE id=:id'), {'id': original.id})
    try:
        response = approve(admin_client, workspace_run, 'partition-orders')
        assert response.status_code == 200, response.json
        assert response.json['action']['result']['source_rows'] == 14000
        assert response.json['action']['result']['full_copy_equivalent']
    finally:
        with app.app_context(), db.engine.begin() as conn:
            conn.execute(text('UPDATE public.orders SET order_date=:day WHERE id=:id'), {'id': original.id, 'day': original.order_date})
