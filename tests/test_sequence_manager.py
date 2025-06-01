# Test suite for SequenceManager
import pytest
from process_manager import ProcessManager
from sequence_manager import SequenceManager
import contextlib

def test_sequence_manager_init():
    config = {'step1': {'gpu_intensive': False}}
    logger = type('L', (), {})()
    pm = ProcessManager(config, logger)
    sm = SequenceManager(pm, logger)
    assert sm.process_manager is pm

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
    monkeypatch.setattr('process_manager.gpu_manager', type('G', (), {'gpu_session': lambda *a, **k: contextlib.nullcontext()} )())
    result = sm.execute_sequence_worker(['step1', 'step2'], sequence_type="TestSeq")
    assert result is False
    assert sm.get_last_outcome()['status'] == 'failed'
    assert pm.process_info['step1']['status'] == 'failed'
    assert pm.process_info['step2']['status'] == 'idle'

# Add more tests for sequence logic as needed
