# Basic Flask app tests for app_new.py
import pytest
from app_new import APP_FLASK

@pytest.fixture
def client():
    APP_FLASK.config['TESTING'] = True
    with APP_FLASK.test_client() as client:
        yield client

def test_get_config(client):
    resp = client.get('/api/get_config')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'base_paths' in data

def test_get_process_info(client):
    resp = client.get('/api/get_process_info')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
