"""Tests for the runtime model picker."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

import app.api.settings as settings_mod
from app.api.settings import get_runtime_model, MODEL_FAMILIES


@pytest.fixture
def runtime_path(tmp_path, monkeypatch):
    p = tmp_path / "runtime_settings.json"
    monkeypatch.setattr(settings_mod, "RUNTIME_SETTINGS_PATH", p)
    return p


def test_no_file_means_no_override(runtime_path):
    assert get_runtime_model() is None


def test_override_round_trip(runtime_path):
    runtime_path.write_text(json.dumps({"llm_model": "deepseek/deepseek-chat"}))
    assert get_runtime_model() == "deepseek/deepseek-chat"


def test_corrupt_file_is_safe(runtime_path):
    runtime_path.write_text("{not json")
    assert get_runtime_model() is None


def test_families_cover_billys_four():
    prefixes = set(MODEL_FAMILIES)
    assert {"anthropic/", "openai/", "deepseek/", "moonshotai/"} == prefixes


def test_llm_client_prefers_runtime_model(runtime_path, monkeypatch):
    runtime_path.write_text(json.dumps({"llm_model": "moonshotai/kimi-k3"}))
    from app.utils.llm_client import LLMClient
    monkeypatch.setattr("app.config.Config.LLM_API_KEY", "test-key")
    client = LLMClient()
    assert client.model == "moonshotai/kimi-k3"
    # Explicit constructor arg still wins
    client2 = LLMClient(model="anthropic/claude-sonnet-4.6")
    assert client2.model == "anthropic/claude-sonnet-4.6"
