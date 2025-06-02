import threading
import time
import pytest
from gpu_manager import GPUManager, GpuUnavailableError

@pytest.fixture(autouse=True, scope="module")
def restore_threading_in_concurrency_module():
    """Fixture pour restaurer threading.Thread après tous les tests de ce module."""
    original_thread_class = threading.Thread
    print(f"MODULE_FIXTURE (concurrency): Saved original threading.Thread")
    yield
    threading.Thread = original_thread_class
    print(f"MODULE_FIXTURE (concurrency): Restored original threading.Thread")

def test_gpu_manager_concurrent_access():
    logger = type('L', (), {'info': lambda *a, **k: None, 'warning': lambda *a, **k: None, 'error': lambda *a, **k: None, 'debug': lambda *a, **k: None})()
    manager = GPUManager(logger, wait_timeout=2)
    
    # AJOUT : Définir une configuration de commandes pour le test
    test_commands_config = {
        "A": {"gpu_intensive": True},
        "B": {"gpu_intensive": True}
    }
    manager.set_commands_config(test_commands_config)
    
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
    from gpu_manager import GPUManager, GpuUnavailableError
    import time
    import pytest
    import threading
    
    logger = type('L', (), {
        'info': lambda *a, **k: None, 
        'warning': lambda *a, **k: None, 
        'error': lambda *a, **k: None,
        'debug': lambda *a, **k: None
    })()
    
    # Créer le manager avec un timeout court
    manager = GPUManager(logger, wait_timeout=0.2)
    
    # Configurer les commandes pour que A et B soient des tâches GPU intensives
    test_commands_config = {
        'A': {'gpu_intensive': True},
        'B': {'gpu_intensive': True}
    }
    manager.set_commands_config(test_commands_config)
    
    results = []
    
    def gpu_task():
        try:
            # S'assurer que A prend le GPU, même s'il était occupé
            with manager.gpu_session("A", wait_if_busy=True):
                results.append("A_acquired")
                time.sleep(0.5)  # Bloquer le GPU pendant 0.5s
                results.append("A_released")
        except Exception as e:
            results.append(f"A_error: {str(e)}")
    
    # Démarrer la tâche A qui prend le GPU
    t1 = threading.Thread(target=gpu_task)
    t1.start()
    time.sleep(0.05)  # Attendre que A ait pris le GPU
    
    # Vérifier que B ne peut pas prendre le GPU (timeout après 0.2s)
    with pytest.raises(GpuUnavailableError):
        with manager.gpu_session("B", wait_if_busy=True):
            results.append("B_acquired")  # Ne devrait jamais être exécuté
    
    # Attendre que A termine
    t1.join()
    
    # Vérifier que A a bien acquis et libéré le GPU
    assert "A_acquired" in results
    assert "A_released" in results
    assert "B_acquired" not in results

def test_gpu_manager_interrupt():
    logger = type('L', (), {'info': lambda *a, **k: None, 'warning': lambda *a, **k: None, 'error': lambda *a, **k: None, 'debug': lambda *a, **k: None})()
    manager = GPUManager(logger, wait_timeout=2)
    
    # AJOUT : Définir une configuration de commandes pour le test
    test_commands_config = {
        "A": {"gpu_intensive": True},
        "B": {"gpu_intensive": True}
    }
    manager.set_commands_config(test_commands_config)
    
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
