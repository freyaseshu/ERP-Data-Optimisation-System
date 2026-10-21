from scripts.validate_dataset import validate_dataset
from scripts.generate_dataset import generate_dataset,SIZES

def test_row_counts_integrity_and_money(app):
    with app.app_context():
        result=validate_dataset()
        assert result['success'],result
        assert result['total_erp_records']==77220
        assert result['counts']==SIZES['medium']

def test_rerun_preserves_existing_data_and_users(app):
    from models.user import User
    with app.app_context():
        password=User.query.filter_by(username='admin').one().password
        actual=generate_dataset('large')
        assert actual==SIZES['medium']
        assert User.query.filter_by(username='admin').one().password==password

def test_configurable_sizes():
    assert sum(SIZES['small'].values())<50000
    assert sum(SIZES['medium'].values())>=50000
    assert sum(SIZES['large'].values())>=100000

import pytest

@pytest.mark.parametrize('profile',['small','large'])
def test_other_sizes_with_actual_database(fresh_database,profile):
    with fresh_database():
        counts=generate_dataset(profile)
        assert counts==SIZES[profile]
        assert validate_dataset()['success']

def test_generation_failure_is_atomic(fresh_database):
    from sqlalchemy import event
    from utils.db import db
    with fresh_database():
        def fail_orders(conn,cursor,statement,parameters,context,executemany):
            if statement.startswith('INSERT INTO orders'):
                raise RuntimeError('Injected generator failure')
        event.listen(db.engine,'before_cursor_execute',fail_orders)
        try:
            with pytest.raises(RuntimeError,match='Injected generator failure'):
                generate_dataset('small')
        finally:event.remove(db.engine,'before_cursor_execute',fail_orders)
        with db.engine.connect() as conn:
            for table in SIZES['small']:
                assert conn.exec_driver_sql('SELECT count(*) FROM '+table).scalar()==0
