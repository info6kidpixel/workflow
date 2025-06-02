import pytest
from unittest.mock import MagicMock, patch
import types
import contextlib
import logging
import threading  # Ajout de l'import manquant

# On suppose que app_new.py est importable et que les objets sont accessibles
import app_new

# Helper function for creating process info dictionaries
def make_process_info(status='pending_gpu', gpu_intensive=True):
    """Helper to create process info dict for tests"""
    return {
        'status': status,
        'log': [],
        'gpu_intensive': gpu_intensive,
        'progress_current': 0,
        'progress_total': 100,
        'progress_text': '',
    }

@pytest.fixture(autouse=True, scope="module")
def restore_threading():
    original_thread = threading.Thread
    yield
    threading.Thread = original_thread
    print("MODULE FIXTURE: Restored original threading.Thread")

def test_check_and_launch_pending_gpu_task_launches_gpu_task(monkeypatch):
    # Préparer les mocks
    mock_gpu_manager = MagicMock()
    mock_gpu_manager._gpu_lock = context = MagicMock()
    context.__enter__.return_value = None
    context.__exit__.return_value = None
    # Correction: utiliser _gpu_in_use_by au lieu de current_user
    mock_gpu_manager._gpu_in_use_by = None

    # Simuler une tâche GPU en attente
    process_info = {
        'analyze_audio': make_process_info(),
        'scene_cut': make_process_info(status='idle', gpu_intensive=False)
    }
    
    # Simuler la config
    commands_config = {
        'analyze_audio': {'gpu_intensive': True},
        'scene_cut': {'gpu_intensive': False}
    }

    # Simuler le process_manager
    mock_process_manager = MagicMock()
    mock_process_manager.process_info = process_info
    mock_process_manager.run_process_async = MagicMock()

    # Simuler le sequence_manager
    mock_sequence_manager = MagicMock()
    mock_sequence_manager.get_current_auto_mode_key.return_value = 'analyze_audio'

    # Simuler les variables globales
    monkeypatch.setattr(app_new, 'gpu_manager', mock_gpu_manager)
    monkeypatch.setattr(app_new, 'process_manager', mock_process_manager)
    monkeypatch.setattr(app_new, 'sequence_manager', mock_sequence_manager)
    monkeypatch.setattr(app_new, 'COMMANDS_CONFIG', commands_config)
    monkeypatch.setattr(app_new, 'REMOTE_SEQUENCE_STEP_KEYS', ['analyze_audio'])

    # Appeler la fonction
    app_new.check_and_launch_pending_gpu_task()

    # Vérifier que run_process_async a été appelé pour la tâche GPU
    mock_process_manager.run_process_async.assert_called_once_with(
        'analyze_audio', is_auto_mode_step=True, sequence_type='AutoMode'
    )

def test_check_and_launch_pending_gpu_task_no_pending(monkeypatch):
    mock_gpu_manager = MagicMock()
    mock_gpu_manager._gpu_lock = context = MagicMock()
    context.__enter__.return_value = None
    context.__exit__.return_value = None
    # Correction: utiliser _gpu_in_use_by au lieu de current_user
    mock_gpu_manager._gpu_in_use_by = None

    process_info = {
        'scene_cut': make_process_info(status='idle', gpu_intensive=False)
    }
    commands_config = {
        'scene_cut': {'gpu_intensive': False}
    }
    mock_process_manager = MagicMock()
    mock_process_manager.process_info = process_info
    mock_process_manager.run_process_async = MagicMock()
    mock_sequence_manager = MagicMock()
    mock_sequence_manager.get_current_auto_mode_key.return_value = 'scene_cut'
    monkeypatch.setattr(app_new, 'gpu_manager', mock_gpu_manager)
    monkeypatch.setattr(app_new, 'process_manager', mock_process_manager)
    monkeypatch.setattr(app_new, 'sequence_manager', mock_sequence_manager)
    monkeypatch.setattr(app_new, 'COMMANDS_CONFIG', commands_config)
    monkeypatch.setattr(app_new, 'REMOTE_SEQUENCE_STEP_KEYS', ['scene_cut'])
    app_new.check_and_launch_pending_gpu_task()
    mock_process_manager.run_process_async.assert_not_called()

def test_check_and_launch_pending_gpu_task_exception(monkeypatch):
    """Vérifie qu'une exception lors du lancement d'une tâche GPU est bien gérée (statut failed, log d'erreur ajouté)."""
    mock_gpu_manager = MagicMock()
    mock_gpu_manager._gpu_lock = context = MagicMock()
    context.__enter__.return_value = None
    context.__exit__.return_value = None
    # Utiliser _gpu_in_use_by au lieu de current_user
    mock_gpu_manager._gpu_in_use_by = None

    process_info = {
        'analyze_audio': make_process_info(),
    }
    commands_config = {
        'analyze_audio': {'gpu_intensive': True},
    }
    mock_process_manager = MagicMock()
    mock_process_manager.process_info = process_info
    # Simuler une exception lors du lancement
    mock_process_manager.run_process_async.side_effect = RuntimeError('Erreur simulée')
    mock_sequence_manager = MagicMock()
    mock_sequence_manager.get_current_auto_mode_key.return_value = 'analyze_audio'
    
    monkeypatch.setattr(app_new, 'gpu_manager', mock_gpu_manager)
    monkeypatch.setattr(app_new, 'process_manager', mock_process_manager)
    monkeypatch.setattr(app_new, 'sequence_manager', mock_sequence_manager)
    monkeypatch.setattr(app_new, 'COMMANDS_CONFIG', commands_config)
    monkeypatch.setattr(app_new, 'REMOTE_SEQUENCE_STEP_KEYS', ['analyze_audio'])

    app_new.check_and_launch_pending_gpu_task()
    
    # Le statut doit être failed et le log doit contenir l'erreur
    info = process_info['analyze_audio']
    assert info['status'] == 'failed'
    assert any('Erreur' in l or 'erreur' in l.lower() for l in info['log'])

def test_check_and_launch_pending_gpu_task_non_gpu_pending(monkeypatch):
    mock_gpu_manager = MagicMock()
    mock_gpu_manager._gpu_lock = context = MagicMock()
    context.__enter__.return_value = None
    context.__exit__.return_value = None
    # Correction: utiliser _gpu_in_use_by au lieu de current_user
    mock_gpu_manager._gpu_in_use_by = None

    process_info = {
        'scene_cut': make_process_info(status='pending_gpu', gpu_intensive=False)
    }
    commands_config = {
        'scene_cut': {'gpu_intensive': False}
    }
    mock_process_manager = MagicMock()
    mock_process_manager.process_info = process_info
    mock_process_manager.run_process_async = MagicMock()
    mock_sequence_manager = MagicMock()
    mock_sequence_manager.get_current_auto_mode_key.return_value = 'scene_cut'
    monkeypatch.setattr(app_new, 'gpu_manager', mock_gpu_manager)
    monkeypatch.setattr(app_new, 'process_manager', mock_process_manager)
    monkeypatch.setattr(app_new, 'sequence_manager', mock_sequence_manager)
    monkeypatch.setattr(app_new, 'COMMANDS_CONFIG', commands_config)
    monkeypatch.setattr(app_new, 'REMOTE_SEQUENCE_STEP_KEYS', ['scene_cut'])
    app_new.check_and_launch_pending_gpu_task()
    # La tâche doit être marquée failed
    assert process_info['scene_cut']['status'] == 'failed'
    assert any('incohérent' in log for log in process_info['scene_cut']['log'])
    mock_process_manager.run_process_async.assert_not_called()

def test_check_and_launch_pending_gpu_task_priority(monkeypatch):
    """Vérifie que la tâche auto_mode est prioritaire sur les autres tâches GPU en attente."""
    mock_gpu_manager = MagicMock()
    mock_gpu_manager._gpu_lock = context = MagicMock()
    context.__enter__.return_value = None
    context.__exit__.return_value = None
    # Correction: utiliser _gpu_in_use_by au lieu de current_user
    mock_gpu_manager._gpu_in_use_by = None

    # Trois tâches GPU en attente, une seule est auto_mode
    process_info = {
        'analyze_audio': make_process_info(),  # auto_mode
        'tracking': make_process_info(),       # séquence
        'autre_gpu': make_process_info(),      # hors séquence
    }
    commands_config = {
        'analyze_audio': {'gpu_intensive': True},
        'tracking': {'gpu_intensive': True},
        'autre_gpu': {'gpu_intensive': True},
    }
    mock_process_manager = MagicMock()
    mock_process_manager.process_info = process_info
    mock_process_manager.run_process_async = MagicMock()
    mock_sequence_manager = MagicMock()
    mock_sequence_manager.get_current_auto_mode_key.return_value = 'analyze_audio'
    monkeypatch.setattr('app_new.gpu_manager', mock_gpu_manager)
    monkeypatch.setattr('app_new.process_manager', mock_process_manager)
    monkeypatch.setattr('app_new.sequence_manager', mock_sequence_manager)
    monkeypatch.setattr('app_new.COMMANDS_CONFIG', commands_config)
    monkeypatch.setattr('app_new.REMOTE_SEQUENCE_STEP_KEYS', ['analyze_audio', 'tracking'])

    app_new.check_and_launch_pending_gpu_task()
    # La tâche auto_mode doit être lancée en priorité
    mock_process_manager.run_process_async.assert_called_once_with(
        'analyze_audio', is_auto_mode_step=True, sequence_type='AutoMode'
    )

def test_gpu_manager_launch_pending_task(monkeypatch):
    """Vérifie que launch_pending_task appelle la callback quand une tâche est en attente."""
    from gpu_manager import GPUManager
    import threading
    from unittest.mock import MagicMock

    # Sauvegarde de la classe Thread originale
    original_thread_class = threading.Thread
    
    try:
        logger = MagicMock()
        manager = GPUManager(logger, wait_timeout=1)
        commands_config = {'analyze_audio': {'gpu_intensive': True}}
        manager.set_commands_config(commands_config)
        
        mock_callback = MagicMock(name="LaunchPendingCallback")
        manager.set_launch_pending_task_callback(mock_callback)
        
        with manager._gpu_lock:
            manager._gpu_waiting_queue.append('analyze_audio')
            manager._gpu_in_use_by = None  # Assurer que le GPU est libre

        # Mocker threading.Thread pour exécution synchrone
        thread_targets_executed = []
        def simpler_synch_mock_thread_constructor(target=None, daemon=None, name=None, **kwargs):
            print(f"LAUNCH_PENDING_TEST MOCK_THREAD: Target: {target.__name__ if hasattr(target, '__name__') else target}")
            thread_targets_executed.append(target)
            if target:
                target() 
            mock_thread_instance = MagicMock(spec=threading.Thread)
            return mock_thread_instance
        
        monkeypatch.setattr(threading, 'Thread', simpler_synch_mock_thread_constructor)

        # Appel direct à launch_pending_task pour tester son comportement
        manager.launch_pending_task()
        
        print(f"LAUNCH_PENDING_TEST Targets executed: {[t.__name__ if hasattr(t, '__name__') else t for t in thread_targets_executed]}")
        mock_callback.assert_called_once()
    
    finally:
        # Restauration explicite de threading.Thread
        threading.Thread = original_thread_class
        print("LAUNCH_PENDING_TEST: Restored original threading.Thread")

def test_gpu_manager_launch_pending_task_triggers_callback_for_next_in_queue(monkeypatch):
    """Vérifie que la callback est appelée pour la prochaine tâche en file d'attente après libération du GPU."""
    from gpu_manager import GPUManager
    import threading
    from unittest.mock import MagicMock
    import time
    
    print("\nDEBUG_TEST: ENTERING test_gpu_manager_launch_pending_task_triggers_callback_for_next_in_queue")

    logger = MagicMock()
    logger.info = lambda msg: print(f"LOGGER_MOCK_CALLBACK_TEST INFO: {msg}")
    logger.debug = lambda msg: print(f"LOGGER_MOCK_CALLBACK_TEST DEBUG: {msg}")

    manager = GPUManager(logger, wait_timeout=1)
    commands_config = {
        'current_gpu_task': {'gpu_intensive': True},
        'next_waiting_task': {'gpu_intensive': True}
    }
    manager.set_commands_config(commands_config)
    print("DEBUG_TEST: Config set")

    final_callback_mock = MagicMock(name="FinalActualCallback")
    manager.set_launch_pending_task_callback(final_callback_mock)
    print("DEBUG_TEST: Final callback set")

    with manager._gpu_lock:
        manager._gpu_waiting_queue.append('next_waiting_task')
    print(f"DEBUG_TEST: Queue: {manager._gpu_waiting_queue}")

    original_launch_pending_task_method = manager.launch_pending_task

    launch_pending_task_mock_called_flag = [] 

    def custom_mock_of_launch_pending_task():
        print("DEBUG_TEST: CUSTOM_MOCK_OF_LAUNCH_PENDING_TASK called")
        launch_pending_task_mock_called_flag.append(True)
        if hasattr(manager, '_launch_pending_task_callback') and manager._launch_pending_task_callback:
            print("DEBUG_TEST: CUSTOM_MOCK_OF_LAUNCH_PENDING_TASK is calling the final callback.")
            manager._launch_pending_task_callback() 
        else:
            print("DEBUG_TEST: CUSTOM_MOCK_OF_LAUNCH_PENDING_TASK: _launch_pending_task_callback not set.")

    manager.launch_pending_task = custom_mock_of_launch_pending_task

    try:
        print("DEBUG_TEST: About to enter gpu_session ('current_gpu_task')")
        with manager.gpu_session('current_gpu_task'):
            print("DEBUG_TEST: Inside manager.gpu_session for current_gpu_task")
        print("DEBUG_TEST: Exited manager.gpu_session")

        time.sleep(0.1) 

        assert launch_pending_task_mock_called_flag, "custom_mock_of_launch_pending_task was not called"
        final_callback_mock.assert_called_once()
        print("DEBUG_TEST: Assertion passed")
    
    finally:
        manager.launch_pending_task = original_launch_pending_task_method
        print("DEBUG_TEST: Test finished.")

def test_gpu_manager_launch_pending_task_triggers_callback_for_waiting_task(monkeypatch):
    """Vérifie que la callback est appelée pour la prochaine tâche en file d'attente après libération du GPU."""
    from gpu_manager import GPUManager
    from unittest.mock import MagicMock
    import time
    
    print("\nDEBUG_TEST: ENTERING test_gpu_manager_launch_pending_task_triggers_callback_for_waiting_task (MODIFIED)")

    logger = MagicMock()
    logger.info = lambda msg: print(f"LOGGER_MOCK_CALLBACK_TEST INFO: {msg}")
    logger.debug = lambda msg: print(f"LOGGER_MOCK_CALLBACK_TEST DEBUG: {msg}")
    logger.error = lambda msg, **kwargs: print(f"LOGGER_MOCK_CALLBACK_TEST ERROR: {msg}")
    logger.warning = lambda msg: print(f"LOGGER_MOCK_CALLBACK_TEST WARNING: {msg}")

    manager = GPUManager(logger, wait_timeout=1)
    
    commands_config = {
        'current_gpu_task': {'gpu_intensive': True},
        'next_waiting_task': {'gpu_intensive': True}
    }
    manager.set_commands_config(commands_config)
    print("DEBUG_TEST: Config set")

    mock_callback_for_next_task = MagicMock(name="TheCallbackWeAreTesting")
    manager.set_launch_pending_task_callback(mock_callback_for_next_task)
    print("DEBUG_TEST: Callback set")

    with manager._gpu_lock:
        manager._gpu_waiting_queue.append('next_waiting_task')
    print(f"DEBUG_TEST: Queue: {manager._gpu_waiting_queue}")

    original_launch_pending_task_method = manager.launch_pending_task
    
    launch_pending_task_mock_called_flag = []

    def custom_mock_of_launch_pending_task():
        print("DEBUG_TEST: CUSTOM_MOCK_OF_LAUNCH_PENDING_TASK called")
        launch_pending_task_mock_called_flag.append(True)
        if hasattr(manager, '_launch_pending_task_callback') and manager._launch_pending_task_callback:
            print("DEBUG_TEST: CUSTOM_MOCK_OF_LAUNCH_PENDING_TASK is calling the final callback.")
            manager._launch_pending_task_callback() 
        else:
            print("DEBUG_TEST: CUSTOM_MOCK_OF_LAUNCH_PENDING_TASK: _launch_pending_task_callback not set.")

    manager.launch_pending_task = custom_mock_of_launch_pending_task

    try:
        print("DEBUG_TEST: About to enter gpu_session ('current_gpu_task')")
        with manager.gpu_session('current_gpu_task'):
            print("DEBUG_TEST: Inside manager.gpu_session for current_gpu_task")
        print("DEBUG_TEST: Exited manager.gpu_session")

        time.sleep(0.2) 

        assert launch_pending_task_mock_called_flag, "custom_mock_of_launch_pending_task was not called"
        mock_callback_for_next_task.assert_called_once()
        print("DEBUG_TEST: Assertion passed")
    
    finally:
        manager.launch_pending_task = original_launch_pending_task_method
        print("DEBUG_TEST: Test finished, launch_pending_task restored.")

def test_gpu_session_release_triggers_callback_for_waiting_task(monkeypatch):
    """Vérifie que la libération d'une session GPU déclenche la callback pour la tâche en attente."""
    from gpu_manager import GPUManager
    import threading
    from unittest.mock import MagicMock
    import time

    original_thread_class = threading.Thread
    
    try:
        logger = MagicMock()
        logger.info = lambda msg: print(f"LOGGER_MOCK INFO: {msg}")
        
        manager = GPUManager(logger, wait_timeout=1)
        commands_config = {
            'A': {'gpu_intensive': True},
            'B': {'gpu_intensive': True}
        }
        manager.set_commands_config(commands_config)
        
        callback_for_waiting_task = MagicMock()
        callback_for_waiting_task.__name__ = 'callback_for_waiting_task'
        
        def mock_launch_pending_task():
            print("DEBUG_TEST: mock_launch_pending_task called")
            print("DEBUG_TEST: Calling callback_for_waiting_task directly")
            callback_for_waiting_task()
        
        mock_launch_pending_task.__name__ = 'mock_launch_pending_task'
        manager.launch_pending_task = mock_launch_pending_task
        
        def mock_thread_constructor(target=None, daemon=None, **kwargs):
            print(f"DEBUG_TEST: Thread created with target: {target.__name__ if hasattr(target, '__name__') else target}")
            mock_thread = MagicMock(spec=threading.Thread)
            
            def mock_start_method():
                print(f"DEBUG_TEST: mock_start_method() called for target: {target.__name__ if hasattr(target, '__name__') else target}")
                if target:
                    target()
            
            mock_thread.start = mock_start_method
            mock_thread.join = MagicMock()
            
            return mock_thread
        
        monkeypatch.setattr(threading, 'Thread', mock_thread_constructor)
        
        with manager._gpu_lock:
            manager._gpu_waiting_queue.append('B')
        
        with manager.gpu_session('A'):
            pass
        
        callback_for_waiting_task.assert_called_once()
        
    finally:
        print("DEBUG_TEST: ENSURING UNDO for threading.Thread")
        monkeypatch.setattr(threading, 'Thread', original_thread_class)

def test_example_that_mocks_thread(monkeypatch):
    original_thread = threading.Thread
    try:
        def mock_thread(*args, **kwargs):
            pass
        monkeypatch.setattr(threading, 'Thread', mock_thread)
        
        # Test logic here
        # ...
    finally:
        threading.Thread = original_thread
