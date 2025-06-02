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
    """Mock process class for testing"""
    def __init__(self, output_lines, return_code=0):
        # Rendre stdout directement itérable
        self.stdout = iter(output_lines)
        self._return_code = return_code
        self.pid = 12345
        self.terminated = False
        self.killed = False
    
    def poll(self):
        return None if not self.terminated and not self.killed else self._return_code
    
    def terminate(self):
        self.terminated = True
    
    def kill(self):
        self.killed = True
    
    def wait(self, timeout=None):
        if not self.terminated and not self.killed:
            if timeout:
                raise Exception("Process timeout")
        return self._return_code

def test_worker_run_process(monkeypatch):
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
    dummy_proc = DummyProcess(['output line\n'], return_code=0)
    monkeypatch.setattr('process_manager.subprocess.Popen', lambda *a, **kw: dummy_proc)
    
    # Correction: Patcher l'attribut sur l'instance pm
    mock_gpu = type('G', (), {'gpu_session': lambda *a, **k: contextlib.nullcontext()})()
    monkeypatch.setattr(pm, 'gpu_manager', mock_gpu)
    
    # Reste du test...
    pm._worker_run_process('step1')
    assert pm.process_info['step1']['status'] == 'completed'

def test_worker_run_process_gpu_intensive(monkeypatch):
    config = {
        'test_gpu_cmd': {
            'gpu_intensive': True,
            'cmd': ['echo', 'test_gpu'],  # Assurez-vous que la clé est 'cmd' pour correspondre à ce qui est utilisé dans ProcessManager
            'progress_patterns': {}
        }
    }
    logger = type('L', (), {
        'info': lambda *a, **k: print(*a) if a else None,
        'error': lambda *a, **k: print("ERROR:", *a) if a else None,
        'warning': lambda *a, **k: print("WARNING:", *a) if a else None
    })()
    
    pm = ProcessManager(config, logger)
    
    # Créer un processus simulé avec stdout itérable
    dummy_proc = DummyProcess(['GPU Line 1\n', 'GPU Line 2\n'], return_code=0)
    
    monkeypatch.setattr('process_manager.subprocess', __import__('subprocess'))
    monkeypatch.setattr('process_manager.subprocess.Popen', lambda *a, **kw: dummy_proc)
    
    # Mock du GPU manager pour l'instance pm
    mock_gpu_manager = type('G', (), {
        'gpu_session': lambda step_key, wait_if_busy=False: contextlib.nullcontext()
    })()
    monkeypatch.setattr(pm, 'gpu_manager', mock_gpu_manager)
    
    # Lancer le processus via l'API publique
    pm.run_process_async('test_gpu_cmd')
    
    # Attendre que le processus se termine
    timeout = 5
    start = time.time()
    info = pm.process_info['test_gpu_cmd']
    while info['status'] in ('initiated', 'starting', 'running') and (time.time() - start) < timeout:
        time.sleep(0.05)
    
    # Vérifier les résultats
    assert info['status'] == 'completed', f"Process status is {info['status']}, expected 'completed'"
    assert info['return_code'] == 0
    assert 'GPU Line 1' in info['log']
    assert 'GPU Line 2' in info['log']
