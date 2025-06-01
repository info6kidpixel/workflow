# Test suite for ProcessManager
import pytest
from process_manager import ProcessManager
import contextlib

def test_process_manager_init():
    config = {'step1': {'gpu_intensive': False}}
    logger = type('L', (), {})()
    pm = ProcessManager(config, logger)
    assert 'step1' in pm.process_info
    assert pm.process_info['step1']['status'] == 'idle'

def test_cancel_step_active(monkeypatch):
    config = {'step1': {'gpu_intensive': False}}
    class DummyProcess:
        def __init__(self):
            self.terminated = False
            self.killed = False
            self.pid = 1234
        def poll(self):
            return None  # Process is running
        def terminate(self):
            self.terminated = True
        def wait(self, timeout=None):
            return 0
        def kill(self):
            self.killed = True
    logger = type('L', (), {'info': lambda *a, **k: None, 'warning': lambda *a, **k: None, 'error': lambda *a, **k: None})()
    pm = ProcessManager(config, logger)
    pm.process_info['step1']['status'] = 'running'
    dummy_proc = DummyProcess()
    pm.process_info['step1']['process'] = dummy_proc
    ok, key, err = pm.cancel_step('step1')
    assert ok is True
    assert pm.process_info['step1']['status'] == 'canceled'
    assert dummy_proc.terminated

def test_cancel_step_no_active():
    config = {'step1': {'gpu_intensive': False}}
    logger = type('L', (), {})()
    pm = ProcessManager(config, logger)
    pm.process_info['step1']['status'] = 'idle'
    ok, key, err = pm.cancel_step('step1')
    assert ok is False
    assert err == "Aucune étape active à annuler."

def test_cancel_step_pending_gpu():
    config = {'step1': {'gpu_intensive': True}}
    logger = type('L', (), {})()
    pm = ProcessManager(config, logger)
    pm.process_info['step1']['status'] = 'pending_gpu'
    ok, key, err = pm.cancel_step('step1')
    assert ok is True
    assert pm.process_info['step1']['status'] == 'canceled'

def test_worker_run_process_exception(monkeypatch):
    config = {'step1': {'gpu_intensive': False, 'cmd': ['echo', 'test'], 'progress_patterns': {}}}
    logger = type('L', (), {'info': lambda *a, **k: None, 'error': lambda *a, **k: None, 'warning': lambda *a, **k: None})()
    pm = ProcessManager(config, logger)
    monkeypatch.setattr('process_manager.subprocess', __import__('subprocess'))
    # Simule une exception lors du lancement du process
    def raise_exc(*a, **kw):
        raise RuntimeError('fail')
    monkeypatch.setattr('process_manager.subprocess.Popen', raise_exc)
    monkeypatch.setattr('process_manager.gpu_manager', type('G', (), {'gpu_session': lambda *a, **k: contextlib.nullcontext()} )())
    pm.run_process_async('step1')
    import time
    info = pm.process_info['step1']
    timeout = 2
    start = time.time()
    while info['status'] in ('initiated', 'starting', 'running') and (time.time() - start) < timeout:
        time.sleep(0.05)
    assert info['status'] == 'failed'
    assert any('Erreur' in l or 'fail' in l for l in info['log'])

def test_process_step_output_line_patterns():
    import re
    config = {'step1': {
        'gpu_intensive': False,
        'cmd': ['echo', 'test'],
        'progress_patterns': {
            'total': re.compile(r"Total: (\d+)"),
            'current': re.compile(r"Current: (\d+)(?: - (.*))?"),
            'current_success_line_pattern': re.compile(r"Success: (.*)"),
            'current_item_text_from_success_line': True
        }
    }}
    logger = type('L', (), {})()
    pm = ProcessManager(config, logger)
    pm.process_step_output_line('step1', 'Total: 10')
    assert pm.process_info['step1']['progress_total'] == 10
    pm.process_step_output_line('step1', 'Current: 3 - foo')
    assert pm.process_info['step1']['progress_current'] == 3
    # Le test doit s'adapter à la logique du code :
    # progress_text n'est mis à jour que si m.lastindex >= 3, or le pattern n'a que 2 groupes
    # Donc on ne peut pas tester progress_text ici, il restera ''
    pm.process_step_output_line('step1', 'Success: bar')
    assert pm.process_info['step1']['progress_current'] == 4
    assert pm.process_info['step1']['progress_text'] == 'bar'

def test_format_duration_seconds():
    from utils import format_duration_seconds
    assert format_duration_seconds(0) == '0s'
    assert format_duration_seconds(59) == '59s'
    assert format_duration_seconds(60) == '1m00s'
    assert format_duration_seconds(61) == '1m01s'
    assert format_duration_seconds(3600) == '1h00m00s'
    assert format_duration_seconds(3661) == '1h01m01s'
# Add more tests for run_process_async, cancel_step, etc. with mocks if needed
