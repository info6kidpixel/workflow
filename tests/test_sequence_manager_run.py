# Test for SequenceManager.execute_sequence_worker
import pytest
import threading
import time
import contextlib  # Ajout de l'import manquant
from process_manager import ProcessManager
from sequence_manager import SequenceManager

class DummyProcess:
    def __init__(self, lines, return_code=0, delay=0.01):
        self._lines = lines
        self._return_code = return_code
        self._delay = delay
        self.stdout = self
        self._index = 0
        self._closed = False
        self.pid = 1234
    def __iter__(self):
        return self
    def __next__(self):
        if self._index < len(self._lines):
            time.sleep(self._delay)
            line = self._lines[self._index]
            self._index += 1
            return line
        raise StopIteration
    def close(self):
        self._closed = True
    def wait(self):
        return self._return_code
    def poll(self):
        return self._return_code

def test_execute_sequence_worker(monkeypatch):
    config = {
        'step1': {
            'gpu_intensive': False,
            'cmd': ['echo', 'step1'],
            'progress_patterns': {}
        },
        'step2': {
            'gpu_intensive': False,
            'cmd': ['echo', 'step2'],
            'progress_patterns': {}
        }
    }
    logger = type('L', (), {'info': print, 'error': print, 'warning': print})()
    pm = ProcessManager(config, logger)
    sm = SequenceManager(pm, logger)
    dummy_proc = DummyProcess(['ok\n'], return_code=0)
    monkeypatch.setattr('process_manager.subprocess', __import__('subprocess'))
    monkeypatch.setattr('process_manager.subprocess.Popen', lambda *a, **kw: dummy_proc)
    monkeypatch.setattr('process_manager.gpu_manager', type('G', (), {'gpu_session': lambda *a, **k: contextlib.nullcontext()} )())
    # Run sequence
    result = sm.execute_sequence_worker(['step1', 'step2'], sequence_type="TestSeq")
    assert result is True
    assert sm.get_last_outcome()['status'] == 'success'
    assert pm.process_info['step1']['status'] == 'completed'
    assert pm.process_info['step2']['status'] == 'completed'
