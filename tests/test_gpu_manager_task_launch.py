import pytest
from unittest.mock import MagicMock, patch
import threading
import time
from gpu_manager import GPUManager, GpuUnavailableError

@pytest.fixture(autouse=True, scope="module")
def restore_threading_in_task_launch_module():
    """Fixture pour restaurer threading.Thread après tous les tests de ce module."""
    original_thread_class = threading.Thread
    print(f"MODULE_FIXTURE (task_launch): Saved original threading.Thread")
    yield
    threading.Thread = original_thread_class
    print(f"MODULE_FIXTURE (task_launch): Restored original threading.Thread")

def test_gpu_manager_launch_pending_task(monkeypatch):
    """Vérifie que launch_pending_task appelle la callback quand une tâche est en attente et le GPU est libre."""
    logger = MagicMock()
    manager = GPUManager(logger, wait_timeout=1)

    # Configurer la callback mock
    mock_callback = MagicMock()
    manager.set_launch_pending_task_callback(mock_callback)

    # Préparer l'état: GPU libre et une tâche en attente
    with manager._gpu_lock:
        manager._gpu_waiting_queue.append('test_task')
        manager._gpu_in_use_by = None

    # Mocker threading.Thread pour exécuter la callback immédiatement
    original_thread = threading.Thread
    def mock_thread_constructor(target=None, daemon=None, **kwargs):
        mock_thread_instance = MagicMock()
        mock_thread_instance.start = MagicMock()
        
        # Exécuter immédiatement la fonction cible si c'est _launch_pending_task_callback
        if target and target == manager._launch_pending_task_callback:
            target()
            
        return mock_thread_instance
    
    monkeypatch.setattr(threading, 'Thread', mock_thread_constructor)

    # Appeler la fonction à tester
    manager.launch_pending_task()

    # Vérifier que la callback a été appelée
    mock_callback.assert_called_once()

def test_gpu_manager_launch_pending_task_no_tasks(monkeypatch):
    """Vérifie que launch_pending_task n'appelle pas la callback quand aucune tâche n'est en attente."""
    logger = MagicMock()
    manager = GPUManager(logger, wait_timeout=1)

    # Configurer la callback mock
    mock_callback = MagicMock()
    manager.set_launch_pending_task_callback(mock_callback)

    # Préparer l'état: GPU libre mais aucune tâche en attente
    with manager._gpu_lock:
        manager._gpu_waiting_queue.clear()  # S'assurer que la file est vide
        manager._gpu_in_use_by = None

    # Mocker threading.Thread pour exécuter la callback immédiatement si elle est appelée
    original_thread = threading.Thread
    def mock_thread_constructor(target=None, daemon=None, **kwargs):
        mock_thread_instance = MagicMock()
        mock_thread_instance.start = MagicMock()
        
        # Exécuter immédiatement la fonction cible si c'est _launch_pending_task_callback
        if target and target == manager._launch_pending_task_callback:
            target()
            
        return mock_thread_instance
    
    monkeypatch.setattr(threading, 'Thread', mock_thread_constructor)

    # Appeler la fonction à tester
    manager.launch_pending_task()

    # Vérifier que la callback n'a pas été appelée
    mock_callback.assert_not_called()

def test_gpu_manager_launch_pending_task_gpu_in_use(monkeypatch):
    """Vérifie que launch_pending_task n'appelle pas la callback quand le GPU est déjà utilisé."""
    logger = MagicMock()
    manager = GPUManager(logger, wait_timeout=1)

    # Configurer la callback mock
    mock_callback = MagicMock()
    manager.set_launch_pending_task_callback(mock_callback)

    # Préparer l'état: GPU occupé et une tâche en attente
    with manager._gpu_lock:
        manager._gpu_waiting_queue.append('test_task')
        manager._gpu_in_use_by = 'another_task'  # GPU déjà utilisé

    # Mocker threading.Thread pour exécuter la callback immédiatement si elle est appelée
    original_thread = threading.Thread
    def mock_thread_constructor(target=None, daemon=None, **kwargs):
        mock_thread_instance = MagicMock()
        mock_thread_instance.start = MagicMock()
        
        # Exécuter immédiatement la fonction cible si c'est _launch_pending_task_callback
        if target and target == manager._launch_pending_task_callback:
            target()
            
        return mock_thread_instance
    
    monkeypatch.setattr(threading, 'Thread', mock_thread_constructor)

    # Appeler la fonction à tester
    manager.launch_pending_task()

    # Vérifier que la callback n'a pas été appelée
    mock_callback.assert_not_called()

def test_gpu_session_calls_launch_pending_task():
    """Test que gpu_session appelle launch_pending_task lorsque le GPU est libéré."""
    from unittest.mock import MagicMock
    
    # Créer un mock logger
    logger = MagicMock()
    
    # Créer une instance de GPUManager
    manager = GPUManager(logger, wait_timeout=1)
    
    # Configurer commands_config - AJOUT IMPORTANT
    commands_config = {
        'test_task': {'gpu_intensive': True}
    }
    manager.set_commands_config(commands_config)
    
    # Mock la méthode launch_pending_task
    original_launch_pending_task = manager.launch_pending_task
    manager.launch_pending_task = MagicMock()
    
    try:
        # Simuler une acquisition et une libération de la session GPU
        with manager.gpu_session('test_task'):
            # GPU est utilisé par 'test_task'
            pass
        
        # Après la libération du GPU, launch_pending_task devrait être appelé
        # Petit délai pour laisser le temps au thread de s'exécuter
        time.sleep(0.1)
        manager.launch_pending_task.assert_called_once()
    finally:
        # Restaurer la méthode originale
        manager.launch_pending_task = original_launch_pending_task
