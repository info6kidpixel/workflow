import pytest
from app_new import APP_FLASK

@pytest.fixture
def client():
    APP_FLASK.config['TESTING'] = True
    with APP_FLASK.test_client() as client:
        yield client

def test_get_process_info(client):
    resp = client.get('/api/get_process_info')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert 'process_info' in data or 'processInfo' in data

def test_cancel_step_api(client):
    # Suppose au moins une étape existe dans la config
    from app_new import COMMANDS_CONFIG
    step_keys = list(COMMANDS_CONFIG.keys())
    if not step_keys:
        pytest.skip('No step_key in config')
    step_key = step_keys[0]
    resp = client.post(f'/cancel/{step_key}')
    assert resp.status_code in (200, 400, 404)
    # 200 = succès, 400/404 = déjà annulé ou clé inconnue

def test_trigger_render_sequence(client):
    resp = client.post('/api/trigger_render_sequence', json={"sequence_type": "CustomSequence"})
    assert resp.status_code in (200, 400)
    # 200 = séquence lancée, 400 = séquence déjà en cours ou erreur

def test_cancel_step_api_invalid(client):
    resp = client.post('/cancel/step_that_does_not_exist')
    assert resp.status_code in (400, 404)

def test_get_remote_status_summary(client):
    resp = client.get('/api/get_remote_status_summary')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert 'status' in data or 'sequence' in data

def test_trigger_render_sequence_twice(client):
    # Lancer une séquence, puis tenter d'en lancer une autre immédiatement
    resp1 = client.post('/api/trigger_render_sequence', json={"sequence_type": "CustomSequence"})
    resp2 = client.post('/api/trigger_render_sequence', json={"sequence_type": "CustomSequence"})
    assert resp1.status_code in (200, 400)
    assert resp2.status_code == 400  # La deuxième doit échouer si la séquence est déjà en cours
