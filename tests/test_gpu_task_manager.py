import pytest
from unittest.mock import MagicMock, patch
import types

# On suppose que app_new.py est importable et que les objets sont accessibles
import app_new

def make_process_info(status='pending_gpu', gpu_intensive=True):
    return {
        'status': status,
        'log': [],
        'process': None,
        'return_code': None
    }

def test_check_and_launch_pending_gpu_task_launches_gpu_task(monkeypatch):
    # Préparer les mocks
    mock_gpu_manager = MagicMock()
    mock_gpu_manager._gpu_lock = context = MagicMock()
    context.__enter__.return_value = None
    context.__exit__.return_value = None
    mock_gpu_manager.current_user = None

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
    mock_gpu_manager.current_user = None

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

def test_check_and_launch_pending_gpu_task_non_gpu_pending(monkeypatch):
    mock_gpu_manager = MagicMock()
    mock_gpu_manager._gpu_lock = context = MagicMock()
    context.__enter__.return_value = None
    context.__exit__.return_value = None
    mock_gpu_manager.current_user = None

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
    mock_gpu_manager.current_user = None

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

    import app_new
    app_new.check_and_launch_pending_gpu_task()
    # La tâche auto_mode doit être lancée en priorité
    mock_process_manager.run_process_async.assert_called_once_with(
        'analyze_audio', is_auto_mode_step=True, sequence_type='AutoMode'
    )

def test_check_and_launch_pending_gpu_task_exception(monkeypatch):
    """Vérifie qu'une exception lors du lancement d'une tâche GPU est bien gérée (statut failed, log d'erreur ajouté)."""
    mock_gpu_manager = MagicMock()
    mock_gpu_manager._gpu_lock = context = MagicMock()
    context.__enter__.return_value = None
    context.__exit__.return_value = None
    mock_gpu_manager.current_user = None

    process_info = {
        'analyze_audio': make_process_info(),
    }
    commands_config = {
        'analyze_audio': {'gpu_intensive': True},
    }
    mock_process_manager = MagicMock()
    mock_process_manager.process_info = process_info
    # Simule une exception lors du lancement
    mock_process_manager.run_process_async.side_effect = RuntimeError('Erreur simulée')
    mock_sequence_manager = MagicMock()
    mock_sequence_manager.get_current_auto_mode_key.return_value = 'analyze_audio'
    monkeypatch.setattr('app_new.gpu_manager', mock_gpu_manager)
    monkeypatch.setattr('app_new.process_manager', mock_process_manager)
    monkeypatch.setattr('app_new.sequence_manager', mock_sequence_manager)
    monkeypatch.setattr('app_new.COMMANDS_CONFIG', commands_config)
    monkeypatch.setattr('app_new.REMOTE_SEQUENCE_STEP_KEYS', ['analyze_audio'])

    import app_new
    app_new.check_and_launch_pending_gpu_task()
    # Le statut doit être failed et le log doit contenir l'erreur
    info = process_info['analyze_audio']
    assert info['status'] == 'failed'
    assert any('Erreur' in l or 'erreur' in l.lower() for l in info['log'])
