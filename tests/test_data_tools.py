from sqlalchemy import text
from utils.db import db

def test_archive_preserves_live_relationships_and_is_repeatable(admin_client,app):
    with app.app_context(),db.engine.connect() as conn:
        before={t:conn.exec_driver_sql('SELECT count(*) FROM '+t).scalar() for t in ('orders','order_items','payments','transactions')}
    preview=admin_client.post('/api/archive/preview',json={'table':'orders','before_date':'2024-06-01'})
    assert preview.status_code==200
    result=admin_client.post('/api/archive/execute',json={'table':'orders','before_date':'2024-06-01','confirm':True})
    assert result.status_code==200,result.json
    again=admin_client.post('/api/archive/execute',json={'table':'orders','before_date':'2024-06-01','confirm':True})
    assert again.json['data']['records_archived']==0
    with app.app_context(),db.engine.connect() as conn:
        assert before=={t:conn.exec_driver_sql('SELECT count(*) FROM '+t).scalar() for t in before}

def test_duplicate_deletion_rejects_unrelated_records(admin_client):
    response=admin_client.post('/api/duplicates/delete',json={'table':'customers','keep_id':1,'delete_ids':[2],'confirm':True})
    assert response.status_code==400

def test_duplicate_delete_only_unreferenced(admin_client,app):
    with app.app_context(),db.engine.begin() as conn:
        ids=[conn.execute(text("INSERT INTO customers (name,email,city) VALUES (:name,'dup-test@example.invalid','Chicago') RETURNING id"),{'name':'Test duplicate'}).scalar() for _ in range(2)]
    response=admin_client.post('/api/duplicates/delete',json={'table':'customers','keep_id':ids[0],'delete_ids':[ids[1]],'confirm':True})
    assert response.status_code==200,response.json
    with app.app_context(),db.engine.begin() as conn:conn.execute(text('DELETE FROM customers WHERE id=:id'),{'id':ids[0]})

def test_referenced_duplicates_cannot_cascade(admin_client,app):
    with app.app_context(),db.engine.begin() as conn:
        keep,child=conn.exec_driver_sql('SELECT customer_id FROM orders GROUP BY customer_id ORDER BY customer_id LIMIT 2').scalars().all()
        original=conn.execute(text('SELECT email FROM customers WHERE id=:id'),{'id':child}).scalar()
        conn.execute(text('UPDATE customers SET email=(SELECT email FROM customers WHERE id=:keep) WHERE id=:child'),{'keep':keep,'child':child})
    try:
        response=admin_client.post('/api/duplicates/delete',json={'table':'customers','keep_id':keep,'delete_ids':[child],'confirm':True})
        assert response.status_code==400,response.json
        assert 'Referenced' in response.json['message']
    finally:
        with app.app_context(),db.engine.begin() as conn:conn.execute(text('UPDATE customers SET email=:email WHERE id=:id'),{'email':original,'id':child})
