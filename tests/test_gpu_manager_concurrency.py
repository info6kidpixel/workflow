import threading
import time
import pytest
from gpu_manager import GPUManager

def test_gpu_manager_concurrent_access():
    logger = type('L', (), {'info': lambda *a, **k: None, 'warning': lambda *a, **k: None, 'error': lambda *a, **k: None})()
    manager = GPUManager(logger, wait_timeout=2)
    results = []
    def gpu_task(name, delay=0.2):
        with manager.gpu_session(name, wait_if_busy=True):
            results.append(f"{name}_acquired")
            time.sleep(delay)
            results.append(f"{name}_released")
    t1 = threading.Thread(target=gpu_task, args=("A", 0.5))
    t2 = threading.Thread(target=gpu_task, args=("B", 0.1))
    t1.start(); time.sleep(0.05); t2.start()
    t1.join(); t2.join()
    # B doit attendre que A libère le GPU
    assert results == ['A_acquired', 'A_released', 'B_acquired', 'B_released']

def test_gpu_manager_timeout():
    logger = type('L', (), {'info': lambda *a, **k: None, 'warning': lambda *a, **k: None, 'error': lambda *a, **k: None})()
    manager = GPUManager(logger, wait_timeout=0.2)
    results = []
    def gpu_task():
        with manager.gpu_session("A", wait_if_busy=True):
            time.sleep(0.5)
    t1 = threading.Thread(target=gpu_task)
    t1.start(); time.sleep(0.05)
    with pytest.raises(Exception):
        with manager.gpu_session("B", wait_if_busy=True):
            pass
    t1.join()

def test_gpu_manager_interrupt():
    logger = type('L', (), {'info': lambda *a, **k: None, 'warning': lambda *a, **k: None, 'error': lambda *a, **k: None})()
    manager = GPUManager(logger, wait_timeout=2)
    stop_event = threading.Event()
    manager.set_app_stop_event(stop_event)
    results = []
    def gpu_task():
        with manager.gpu_session("A", wait_if_busy=True):
            time.sleep(0.5)
    t1 = threading.Thread(target=gpu_task)
    t1.start(); time.sleep(0.05)
    # Interrompt l'attente du second thread
    def try_acquire():
        try:
            with manager.gpu_session("B", wait_if_busy=True):
                results.append('acquired')
        except Exception as e:
            results.append('interrupted')
    t2 = threading.Thread(target=try_acquire)
    t2.start(); time.sleep(0.1)
    stop_event.set()
    t1.join(); t2.join()
    assert 'interrupted' in results
