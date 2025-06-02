import pytest
from process_manager import ProcessManager
from sequence_manager import SequenceManager
import contextlib
from unittest.mock import MagicMock

def test_sequence_manager_init():
    config = {
        'step1': {'gpu_intensive': False, 'cmd': ['echo', 'test'], 'progress_patterns': {}}
    }
    logger = type('L', (), {
        'info': lambda *a, **k: None,
        'debug': lambda *a, **k: None,
        'error': lambda *a, **k: None,
        'warning': lambda *a, **k: None
    })()
    pm = ProcessManager(config, logger)
    sm = SequenceManager(pm, logger)
    
    # Correction: Vérifier l'égalité avec la valeur attendue au lieu de None
    assert sm.get_last_outcome() == {"status": "never_run", "timestamp": None}

def test_sequence_worker_failure(monkeypatch):
    config = {
        'step1': {'gpu_intensive': False, 'cmd': ['echo', 'fail'], 'progress_patterns': {}},
        'step2': {'gpu_intensive': False, 'cmd': ['echo', 'ok'], 'progress_patterns': {}}
    }
    logger = type('L', (), {'info': lambda *a, **k: None, 'error': lambda *a, **k: None, 'warning': lambda *a, **k: None})()
    pm = ProcessManager(config, logger)
    sm = SequenceManager(pm, logger)
    
    class DummyProcess:
        def __init__(self, lines, return_code=1):
            self.stdout = iter(lines)
            self._return_code = return_code
            self.pid = 1234
        def wait(self, timeout=None):
            return self._return_code
        def poll(self):
            return self._return_code
        def close(self):
            pass
            
    monkeypatch.setattr('process_manager.subprocess', __import__('subprocess'))
    monkeypatch.setattr('process_manager.subprocess.Popen', lambda *a, **kw: DummyProcess(['fail\n'], return_code=1))
    
    # Patch l'instance pm.gpu_manager au lieu du module process_manager.gpu_manager
    mock_gpu = type('G', (), {'gpu_session': lambda *a, **k: contextlib.nullcontext()})()
    monkeypatch.setattr(pm, 'gpu_manager', mock_gpu)
    
    result = sm.execute_sequence_worker(['step1', 'step2'], sequence_type="TestSeq")
    assert result is False
    assert sm.get_last_outcome()['status'] == 'failed'
    assert pm.process_info['step1']['status'] == 'failed'
    assert pm.process_info['step2']['status'] == 'idle'

def test_cancel_step_active(monkeypatch):
    config = {'step1': {'gpu_intensive': False, 'cmd': ['dummy_command']}}
    logger = type('L', (), {
        'info': lambda *a, **k: None,
        'debug': lambda *a, **k: None,
        'error': lambda *a, **k: None,
        'warning': lambda *a, **k: None
    })()
    pm = ProcessManager(config, logger)
    
    dummy_proc = MagicMock()
    dummy_proc.pid = 1234
    dummy_proc.poll.return_value = None  # Process is running
    
    pm.process_info['step1']['status'] = 'running'
    pm.process_info['step1']['process'] = dummy_proc
    
    ok, key, err = pm.cancel_step('step1')
    
    assert ok is True
    assert key == 'step1'
    assert err is None
    dummy_proc.terminate.assert_called_once()
    assert pm.process_info['step1']['status'] == 'canceled'

# Add more tests for sequence logic as needed
