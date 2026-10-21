import pytest

@pytest.mark.parametrize('page', ['/dashboard','/analyser','/optimiser','/explorer','/benchmarks','/reports','/limitations','/duplicates','/archive'])
def test_pages_render(admin_client,page):
    response=admin_client.get(page)
    assert response.status_code==200
    assert b'ERP System' in response.data

@pytest.mark.parametrize('url', ['/api/dashboard/stats','/api/database/status','/api/explorer/tables','/api/explorer/table/orders','/api/explorer/data/customers','/api/limitations','/api/reports/performance','/api/recommendations','/api/benchmarks/history','/api/archive/history','/api/duplicates/customers'])
def test_read_apis(admin_client,url):
    response=admin_client.get(url)
    assert response.status_code==200
    assert response.json['success'],response.json

def test_dashboard_counts(admin_client):
    stats=admin_client.get('/api/dashboard/stats').json['stats']
    assert stats['db_connected']
    assert stats['total_erp_records']==77220
    assert stats['total_tables']==16
    assert 'PostgreSQL' in stats['postgresql_version']

def test_query_modes_and_preview(admin_client):
    for actual in (False,True):
        response=admin_client.post('/api/analyse-query',json={'query':'SELECT id, name FROM customers','run_analyze':actual})
        assert response.status_code==200,response.json
        assert response.json['measurement']==('actual' if actual else 'estimated')
        assert (response.json['execution_time_ms'] is not None)==actual
    response=admin_client.post('/api/execute-query',json={'query':'SELECT id FROM customers'})
    assert len(response.json['rows'])==100
    assert response.json['truncated'] is True

def test_postgres_error_and_recovery(admin_client):
    bad=admin_client.post('/api/analyse-query',json={'query':'SELECT missing_column FROM orders'})
    assert bad.status_code==400
    assert 'does not exist' in bad.json['error']
    assert admin_client.post('/api/analyse-query',json={'query':'SELECT id FROM orders LIMIT 1'}).status_code==200

def test_csv_and_custom_range(admin_client):
    assert admin_client.get('/api/reports/performance?range=custom').status_code==400
    response=admin_client.get('/api/reports/export?range=custom&start=2020-01-01&end=2030-01-01')
    assert response.status_code==200
    assert response.mimetype=='text/csv'
    assert b'Log ID' in response.data
    assert b'Evidence JSON' in response.data

def test_limitations(admin_client):
    response=admin_client.get('/api/limitations').json
    assert response['counts']['total']==12
    assert len(response['limitations'])==12
    assert all(row['test_evidence'] for row in response['limitations'])
    filtered=admin_client.get('/api/limitations?status=Partially%20Implemented').json
    assert all(row['status']=='Partially Implemented' for row in filtered['limitations'])
    assert admin_client.get('/api/limitations?status=invalid').status_code==400

def test_pagination_search_sort(admin_client):
    response=admin_client.get('/api/explorer/data/customers?page=2&per_page=10&sort_by=id&sort_dir=DESC').json
    assert len(response['rows'])==10
    assert response['rows'][0]['id']>response['rows'][-1]['id']
    assert response['page']==2
    search=admin_client.get('/api/explorer/data/customers?search=Chicago&per_page=5').json
    assert len(search['rows'])==5
    assert all(row['city']=='Chicago' for row in search['rows'])

@pytest.mark.parametrize('url', [
 '/api/explorer/data/users','/api/explorer/table/users','/api/explorer/data/customers?per_page=101',
 '/api/explorer/data/customers?page=-1','/api/explorer/data/customers?sort_by=password',
 '/api/explorer/data/customers?sort_dir=DROP',
 '/api/explorer/data/customers?page=abc','/api/explorer/data/customers?per_page=abc',
])
def test_explorer_rejects_invalid(admin_client,url):
    assert admin_client.get(url).status_code==400

def test_benchmark_approval_required(admin_client):
    assert admin_client.post('/api/benchmarks/run',json={'id':'BM-01'}).status_code==400
    assert admin_client.post('/api/benchmarks/run',json={'id':'BM-01','confirm':True,'iterations':100}).status_code==400

def test_connection_unavailable_graceful():
    from app import create_app
    from config import Config
    class Offline(Config):
        TESTING=True
        SQLALCHEMY_BINDS={}
        SQLALCHEMY_DATABASE_URI='postgresql+psycopg://nobody:nothing@127.0.0.1:1/unavailable'
    client=create_app(Offline).test_client()
    with client.session_transaction() as session:session['user_id']=1
    response=client.get('/api/dashboard/stats')
    assert response.status_code==503
    assert response.json['stats']['db_connected'] is False
    assert client.post('/login',data={'username':'x','password':'x'}).status_code==503

def test_controlled_concurrent_reads(app):
    from concurrent.futures import ThreadPoolExecutor
    def worker(_):
        with app.test_client() as client:
            with client.session_transaction() as session:session['user_id']=1
            return [client.get('/api/explorer/data/customers?page=1&per_page=10').status_code for _ in range(5)]
    with ThreadPoolExecutor(max_workers=4) as executor:
        results=list(executor.map(worker,range(4)))
    assert all(code==200 for result in results for code in result)
