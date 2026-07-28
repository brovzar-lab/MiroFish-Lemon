"""
Settings API — /api/settings
Runtime model selection across the four families Lemon uses
(Anthropic, OpenAI GPT, DeepSeek, Moonshot Kimi), listed live from
OpenRouter so model ids never go stale.
"""

import json
import time
from pathlib import Path

import httpx
from flask import Blueprint, jsonify, request

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.api.settings')

settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")

# Runtime override lives next to the other runtime state
RUNTIME_SETTINGS_PATH = Path(Config.UPLOAD_FOLDER) / "runtime_settings.json"

# Model families exposed in the picker: OpenRouter id prefix -> display group
MODEL_FAMILIES = {
    "anthropic/": "Anthropic (Claude)",
    "openai/": "OpenAI (GPT)",
    "deepseek/": "DeepSeek",
    "moonshotai/": "Moonshot (Kimi)",
}

_models_cache = {"at": 0.0, "data": None}
_MODELS_TTL_SECONDS = 3600


def get_runtime_model() -> str | None:
    """Current runtime model override, or None. Used by LLMClient."""
    try:
        if RUNTIME_SETTINGS_PATH.exists():
            data = json.loads(RUNTIME_SETTINGS_PATH.read_text(encoding="utf-8"))
            return data.get("llm_model") or None
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _fetch_openrouter_models():
    now = time.time()
    if _models_cache["data"] and now - _models_cache["at"] < _MODELS_TTL_SECONDS:
        return _models_cache["data"]
    resp = httpx.get("https://openrouter.ai/api/v1/models", timeout=15)
    resp.raise_for_status()
    models = resp.json().get("data", [])
    _models_cache.update(at=now, data=models)
    return models


@settings_bp.route("/models", methods=["GET"])
def list_models():
    """Curated model list grouped by family, fetched live from OpenRouter."""
    try:
        models = _fetch_openrouter_models()
    except Exception as e:
        logger.warning(f"OpenRouter model list unavailable: {e}")
        return jsonify({
            "groups": [],
            "current": get_runtime_model() or Config.LLM_MODEL_NAME,
            "error": "Could not reach OpenRouter for the live model list.",
        }), 502

    groups = {label: [] for label in MODEL_FAMILIES.values()}
    for m in models:
        mid = m.get("id", "")
        for prefix, label in MODEL_FAMILIES.items():
            if mid.startswith(prefix):
                pricing = m.get("pricing", {}) or {}
                groups[label].append({
                    "id": mid,
                    "name": m.get("name", mid),
                    "context_length": m.get("context_length"),
                    "prompt_price": pricing.get("prompt"),
                    "completion_price": pricing.get("completion"),
                })
                break

    for label in groups:
        groups[label].sort(key=lambda x: x["id"])

    return jsonify({
        "groups": [{"label": label, "models": ms} for label, ms in groups.items() if ms],
        "current": get_runtime_model() or Config.LLM_MODEL_NAME,
    })


@settings_bp.route("/model", methods=["GET"])
def get_model():
    return jsonify({
        "model": get_runtime_model() or Config.LLM_MODEL_NAME,
        "source": "runtime" if get_runtime_model() else "env",
    })


@settings_bp.route("/model", methods=["POST"])
def set_model():
    """Body: {model: "anthropic/claude-sonnet-4.6"}. Empty model clears the override."""
    data = request.get_json(silent=True) or {}
    model = (data.get("model") or "").strip()

    if model and not any(model.startswith(p) for p in MODEL_FAMILIES):
        return jsonify({
            "error": f"Model must belong to one of: {', '.join(MODEL_FAMILIES)}"
        }), 400

    RUNTIME_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    current = {}
    try:
        if RUNTIME_SETTINGS_PATH.exists():
            current = json.loads(RUNTIME_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        current = {}
    if model:
        current["llm_model"] = model
    else:
        current.pop("llm_model", None)
    RUNTIME_SETTINGS_PATH.write_text(
        json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    effective = model or Config.LLM_MODEL_NAME
    logger.info(f"LLM model set to: {effective}")
    return jsonify({"status": "ok", "model": effective})
