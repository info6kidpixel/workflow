# Test for ProcessManager._worker_run_process and run_process_async
import pytest
from process_manager import ProcessManager
import threading
import time
import contextlib

class DummyStdout:
    def __init__(self, lines, delay=0.01):
        self._lines = lines
        self._delay = delay
        self._index = 0
        self._closed = False
    def __iter__(self):
        return self
    def __next__(self):
        if self._index < len(self._lines):
            time.sleep(self._delay)
            line = self._lines[self._index]
            self._index += 1
            return line
        raise StopIteration
    def readline(self):
        try:
            return self.__next__()
        except StopIteration:
            return ''
    def close(self):
        self._closed = True

class DummyProcess:
    def __init__(self, lines, return_code=0, delay=0.01):
        self.stdout = DummyStdout(lines, delay)
        self._return_code = return_code
        self.pid = 1234
    def wait(self, timeout=None):
        return self._return_code
    def poll(self):
        return self._return_code


def test_worker_run_process(monkeypatch):
    config = {
        'step1': {
            'gpu_intensive': False,
            'cmd': ['echo', 'test'],
            'progress_patterns': {
                'total': None,
                'current': None
            }
        }
    }
    logger = type('L', (), {'info': print, 'error': print, 'warning': print})()
    pm = ProcessManager(config, logger)
    dummy_lines = ['Line 1\n', 'Line 2\n']
    dummy_proc = DummyProcess(dummy_lines, return_code=0)
    # Patch subprocess.Popen to return dummy process
    monkeypatch.setattr('process_manager.subprocess', __import__('subprocess'))
    monkeypatch.setattr('process_manager.subprocess.Popen', lambda *a, **kw: dummy_proc)
    # Patch gpu_manager
    monkeypatch.setattr('process_manager.gpu_manager', type('G', (), {'gpu_session': lambda *a, **k: contextlib.nullcontext()} )())
    # Run
    pm.run_process_async('step1')
    # Wait for thread to finish (polling)
    timeout = 5
    start = time.time()
    info = pm.process_info['step1']
    while info['status'] in ('initiated', 'starting', 'running') and (time.time() - start) < timeout:
        time.sleep(0.05)
    assert info['status'] == 'completed'
    assert info['return_code'] == 0
    assert 'Line 1' in ''.join(info['log'])
    assert 'Line 2' in ''.join(info['log'])
