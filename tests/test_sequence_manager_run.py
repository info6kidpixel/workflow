import pytest
import threading
import time
import contextlib  # Ajout de l'import manquant
from process_manager import ProcessManager
from sequence_manager import SequenceManager
from tests.helpers import DummyProcess, DummyStdout

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
    
    logger = type('L', (), {
        'info': lambda *a, **k: print(*a) if a else None,
        'error': lambda *a, **k: print("ERROR:", *a) if a else None,
        'warning': lambda *a, **k: print("WARNING:", *a) if a else None,
        'debug': lambda *a, **k: print("DEBUG:", *a) if a else None
    })()
    
    pm = ProcessManager(config, logger)
    sm = SequenceManager(pm, logger)
    
    # Créer un DummyProcess avec stdout itérable
    dummy_proc = DummyProcess(['ok\n'], return_code=0)
    
    monkeypatch.setattr('process_manager.subprocess', __import__('subprocess'))
    monkeypatch.setattr('process_manager.subprocess.Popen', lambda *a, **kw: dummy_proc)
    
    # Correction: patcher l'instance pm.gpu_manager au lieu du module process_manager.gpu_manager
    mock_gpu = type('G', (), {'gpu_session': lambda *a, **k: contextlib.nullcontext()})()
    monkeypatch.setattr(pm, 'gpu_manager', mock_gpu)
    
    # Run sequence
    result = sm.execute_sequence_worker(['step1', 'step2'], sequence_type="TestSeq")
    
    assert result is True
    assert sm.get_last_outcome()['status'] == 'success'
    assert pm.process_info['step1']['status'] == 'completed'
    assert pm.process_info['step2']['status'] == 'completed'
