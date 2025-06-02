import os
import pytest
from app_new import get_token_with_fallback

def test_token_env_var(monkeypatch):
    monkeypatch.setenv('TEST_TOKEN', 'env_value')
    assert get_token_with_fallback('TEST_TOKEN', 'ref_value', 'default', 'TEST_TOKEN') == 'env_value'

def test_token_ref(monkeypatch):
    monkeypatch.delenv('TEST_TOKEN', raising=False)
    assert get_token_with_fallback('TEST_TOKEN', 'ref_value', 'default', 'TEST_TOKEN') == 'ref_value'

def test_token_default(monkeypatch):
    monkeypatch.delenv('TEST_TOKEN', raising=False)
    assert get_token_with_fallback('TEST_TOKEN', '', 'default', 'TEST_TOKEN') == 'default'

def test_token_empty(monkeypatch):
    monkeypatch.delenv('TEST_TOKEN', raising=False)
    assert get_token_with_fallback('TEST_TOKEN', '', None, 'TEST_TOKEN') == ''
