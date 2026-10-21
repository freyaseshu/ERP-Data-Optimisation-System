import pytest
from services.query_optimizer import QueryOptimizerService
from services.benchmark_service import BenchmarkService,BENCHMARK_WORKLOAD
from utils.db import db
from sqlalchemy import text

def test_measurements_and_equivalence(app):
    with app.app_context():
        timing,error=QueryOptimizerService.measure_execution_time('SELECT id FROM customers LIMIT 20',runs=3)
        assert error is None
        assert timing>=0
        same=QueryOptimizerService.verify_query_equivalence('SELECT id FROM customers WHERE id<10 ORDER BY id','SELECT id FROM customers WHERE id<10 ORDER BY id DESC')
        assert same['equivalent'] is True
        different=QueryOptimizerService.verify_query_equivalence('SELECT id FROM customers WHERE id<10','SELECT id FROM customers WHERE id<11')
        assert different['equivalent'] is False

def test_recommendation_apply_audit(admin_client,app):
    response=admin_client.post('/api/optimise-query',json={'query':'SELECT * FROM orders WHERE customer_id=101'})
    assert response.status_code==200,response.json
    index=next(s for s in response.json['suggestions'] if s['type']=='index')
    with app.app_context():
        before=db.session.execute(text('SELECT count(*) FROM query_performance_logs')).scalar()
    applied=admin_client.post('/api/apply-optimization',json={'recommendation_id':index['id'],'confirm':True})
    assert applied.status_code==200,applied.json
    assert applied.json['equivalent'] is True
    with app.app_context():
        from models.optimisation_recommendation import OptimisationRecommendation
        assert db.session.get(OptimisationRecommendation,index['id']).status=='Applied'
        assert db.session.execute(text('SELECT count(*) FROM query_performance_logs')).scalar()>before
    assert admin_client.post('/api/apply-optimization',json={'recommendation_id':index['id'],'confirm':True}).status_code==400

@pytest.mark.parametrize('item',BENCHMARK_WORKLOAD,ids=lambda b:b['id'])
def test_all_benchmarks_equivalence_and_history(app,item):
    with app.app_context():
        result=BenchmarkService.run_benchmark_item(item,iterations=2)
        assert result['success'],result
        assert result['equivalent'] is True
        assert len(result['baseline_samples_ms'])==2
        assert result['dataset_counts']['order_items']==30000
        assert result['baseline_plan']['Plan']
        assert BenchmarkService.get_benchmark_history()
        expected=((result['baseline_time_ms']-result['optimised_time_ms'])/result['baseline_time_ms'])*100
        assert result['improvement_percentage']==pytest.approx(expected)

def test_rerun_does_not_claim_index_creation(app):
    with app.app_context():
        first=BenchmarkService.run_benchmark_item(BENCHMARK_WORKLOAD[0],iterations=1)
        assert first['success']
        again=BenchmarkService.run_benchmark_item(BENCHMARK_WORKLOAD[0],iterations=1)
        assert again['success']
        assert again['index_already_present'] is True
        assert again['index_created'] is False
        assert again['index_applied'] is None

def test_benchmark_rolls_back_on_result_mismatch(app,monkeypatch):
    original=QueryOptimizerService.sample
    calls=[]
    def mismatch(*args,**kwargs):
        data=original(*args,**kwargs)
        calls.append(1)
        if len(calls)==2:data['fingerprint']={'changed':1}
        return data
    with app.app_context():
        monkeypatch.setattr(QueryOptimizerService,'sample',mismatch)
        result=BenchmarkService.run_comparison('SELECT id FROM employees','CREATE INDEX IF NOT EXISTS idx_test_salary ON employees (salary);','rollback test',1)
        assert result['success'] is False
        with db.engine.connect() as conn:
            assert conn.exec_driver_sql("SELECT to_regclass('public.idx_test_salary')").scalar() is None

@pytest.mark.parametrize('iterations',[0,11,True,'3'])
def test_invalid_iterations(app,iterations):
    with app.app_context():
        result=BenchmarkService.run_benchmark_item(BENCHMARK_WORKLOAD[0],iterations=iterations)
        assert result['success'] is False

def test_partial_index_is_not_misreported_as_created(app):
    with app.app_context():
        with db.engine.begin() as conn:
            conn.exec_driver_sql('CREATE INDEX idx_test_partial ON employees (salary) WHERE salary > 100000')
        try:
            result=BenchmarkService.run_comparison('SELECT id FROM employees WHERE salary>0','CREATE INDEX IF NOT EXISTS idx_test_partial ON employees (salary);','partial test',1)
            assert result['success'] is False
            assert 'different relation' in result['error']
        finally:
            with db.engine.begin() as conn:conn.exec_driver_sql('DROP INDEX idx_test_partial')
