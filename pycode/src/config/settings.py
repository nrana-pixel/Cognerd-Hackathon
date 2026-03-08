"""
Canonical project-wide config.
All modules (intelliwrite, aeo_reports, geo_files, database, agents)
should import from here:

    from config.settings import Config
"""

import importlib.util
import logging
import os
import warnings
from functools import lru_cache
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import urlopen, Request

from dotenv import load_dotenv

from utils.log_utils import get_logger
from utils.utils import get_project_root

# Load .env from project root; fall back to src/.env for local setups
_project_root = get_project_root()
_root_env = _project_root / '.env'
_src_env = _project_root / 'src' / '.env'
if _root_env.exists():
    load_dotenv(dotenv_path=_root_env, override=True)
elif _src_env.exists():
    load_dotenv(dotenv_path=_src_env, override=True)
else:
    load_dotenv(override=True)

LOGGER = get_logger(__name__)

_HAS_OLLAMA_DEPENDENCY = importlib.util.find_spec("agno.models.ollama") is not None
_HAS_OLLAMA_RUNTIME = None

OLLAMA_FORWARDING_URL = ""


def _is_ollama_running(base_url: str) -> bool:
    """Check whether the Ollama HTTP API is reachable."""
    if not base_url:
        return False
    try:
        health_endpoint = urljoin(base_url.rstrip('/') + '/', 'api/version')
        req = Request(
            health_endpoint,
            headers={"ngrok-skip-browser-warning": "true", "User-Agent": "IntelliWrite-Ollama-Probe"}
        )
        with urlopen(req, timeout=5) as response:
            return response.status == 200
    except Exception as exc:
        LOGGER.debug("Ollama health probe failed: %s", exc)
        return False


def _has_ollama_support() -> bool:
    """Return True only if the Python dependency is installed and the daemon is reachable."""
    global _HAS_OLLAMA_RUNTIME
    if not _HAS_OLLAMA_DEPENDENCY:
        return False
    if _HAS_OLLAMA_RUNTIME is None:
        _HAS_OLLAMA_RUNTIME = _is_ollama_running(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    return _HAS_OLLAMA_RUNTIME


SUPPORTED_MODELS = {
    "gemini-flash": "models/gemini-flash-latest",
    "gemini-pro": "models/gemini-pro-latest",
    "gemini-1.5-flash": "models/gemini-flash-latest",
    "gemini-1.5-pro": "models/gemini-pro-latest",
}

OPENROUTER_MODEL_ALIASES = {
    "models/gemini-flash-latest": "google/gemini-2.0-flash-001",
    "models/gemini-pro-latest":   "google/gemini-pro-1.5",
    "google/gemini-flash-1.5":    "google/gemini-2.0-flash-001",
    "google/gemini-pro-1.5":      "google/gemini-pro-1.5",
}


def _normalize_non_google_model(model_name: str) -> str:
    if not model_name:
        return None
    return OPENROUTER_MODEL_ALIASES.get(model_name, model_name)


def _normalize_gemini_model(model_name: str) -> str:
    """Map deprecated Gemini model IDs to currently supported ones."""
    if not model_name:
        return "models/gemini-flash-latest"

    normalized = model_name.strip()
    normalized_lower = normalized.lower()

    if normalized_lower.startswith("models/gemini"):
        return normalized

    replacement = SUPPORTED_MODELS.get(normalized_lower)
    if replacement:
        return replacement

    if not normalized_lower.startswith("models/"):
        if normalized_lower in SUPPORTED_MODELS:
            return SUPPORTED_MODELS[normalized_lower]

    warnings.warn(
        f"Model '{model_name}' is not a recognized Gemini model. "
        f"Defaulting to 'models/gemini-flash-latest'.",
        RuntimeWarning,
    )
    return "models/gemini-flash-latest"


GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "aeo_knowledge_base")
    BRAND_COLLECTION_NAME = os.getenv("BRAND_COLLECTION_NAME", "brand_knowledge_base")

    # MongoDB
    MONGODB_URI = os.getenv("MONGODB_URI")
    MONGODB_DB = os.getenv("MONGODB_DB", "welzin")
    MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "intelliwrite_blogs")

    # Database URL — force pg8000 driver and strip unsupported query params
    _raw_db_url = os.getenv("DATABASE_URL", "postgresql+pg8000://user:password@localhost:5432/aeo_blog_db")
    if _raw_db_url.startswith("postgres://"):
        _url_with_driver = _raw_db_url.replace("postgres://", "postgresql+pg8000://", 1)
    elif _raw_db_url.startswith("postgresql://"):
        _url_with_driver = _raw_db_url.replace("postgresql://", "postgresql+pg8000://", 1)
    else:
        _url_with_driver = _raw_db_url

    DATABASE_URL = _url_with_driver.split("?")[0] if "?" in _url_with_driver else _url_with_driver

    LOGGER.info("--- DB CONFIG ---")
    LOGGER.info("Raw URL start: %s...", _raw_db_url[:15])
    LOGGER.info("Final URL start: %s...", DATABASE_URL[:25])
    LOGGER.info("Driver check: %s", 'pg8000' in DATABASE_URL)
    LOGGER.info("-----------------")

    # LLM providers
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    GEMINI_BASE_URL = GEMINI_BASE_URL

    # Ollama
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

    GEMINI_API_KEY = (
        os.getenv("GEMINI_API_KEY") or
        os.getenv("GOOGLE_API_KEY") or
        os.getenv("PLANNER_API_KEY") or
        os.getenv("WRITER_API_KEY") or
        os.getenv("API")
    )
    MODEL_NAME = os.getenv("MODEL_NAME", "models/gemini-flash-latest")

    @staticmethod
    def _provider_value(var_name: str, default: str):
        raw = os.getenv(var_name, default)
        normalized = raw.lower()
        if normalized == "ollama" and not _has_ollama_support():
            LOGGER.warning(
                "%s=ollama requested but Ollama is unavailable; falling back to %s",
                var_name, default,
            )
            return default
        return normalized

    @staticmethod
    def _model_value(env_var: str, default_model: str, provider: str):
        raw = os.getenv(env_var, default_model)
        if provider == "google":
            return _normalize_gemini_model(raw)
        elif provider == "ollama":
            return Config.OLLAMA_MODEL
        return _normalize_non_google_model(raw)

    @staticmethod
    def _api_key_value(env_var: str, default_key: str, provider: str, openrouter_key: str):
        if provider == "google":
            return os.getenv(env_var, default_key) or default_key
        elif provider == "ollama":
            return None
        return os.getenv(env_var, openrouter_key) or openrouter_key or os.getenv("OPENAI_API_KEY")

    @staticmethod
    def _base_url(provider: str, openrouter_base_url: str):
        if provider == "google":
            return GEMINI_BASE_URL
        elif provider == "ollama":
            return Config.OLLAMA_BASE_URL
        return openrouter_base_url


# --- Resolve defaults after Config class is defined ---

def _determine_default_provider() -> str:
    explicit = os.getenv("DEFAULT_LLM_PROVIDER")
    if explicit:
        normalized = explicit.strip().lower()
        if normalized == "ollama" and not _has_ollama_support():
            LOGGER.warning("DEFAULT_LLM_PROVIDER=ollama requested but Ollama is unavailable; falling back to OpenRouter")
        elif normalized == "openrouter" and not Config.OPENROUTER_API_KEY:
            LOGGER.warning("DEFAULT_LLM_PROVIDER=openrouter requested but OPENROUTER_API_KEY is missing; falling back to Google")
        elif normalized == "google" and not Config.GEMINI_API_KEY:
            LOGGER.warning("DEFAULT_LLM_PROVIDER=google requested but GEMINI_API_KEY is missing; falling back to OpenRouter")
        else:
            return normalized

    if Config.OPENROUTER_API_KEY:
        return "openrouter"
    if Config.GEMINI_API_KEY:
        return "google"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if _has_ollama_support():
        return "ollama"
    return "google"


def _determine_default_model(provider: str) -> str:
    base_model = os.getenv("LLM_MODEL", Config.MODEL_NAME)
    if provider == "google":
        return _normalize_gemini_model(base_model)
    if provider == "ollama":
        return Config.OLLAMA_MODEL
    return _normalize_non_google_model(base_model)


def _determine_default_api_key(provider: str):
    if provider == "google":
        return Config.GEMINI_API_KEY
    if provider == "openrouter":
        return Config.OPENROUTER_API_KEY or os.getenv("OPENAI_API_KEY")
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY")
    if provider == "ollama":
        return None
    return os.getenv("OPENAI_API_KEY") or Config.OPENROUTER_API_KEY


_DEFAULT_LLM_PROVIDER = _determine_default_provider()
_DEFAULT_LLM_MODEL = _determine_default_model(_DEFAULT_LLM_PROVIDER)
_DEFAULT_LLM_API_KEY = _determine_default_api_key(_DEFAULT_LLM_PROVIDER)

Config.DEFAULT_LLM_PROVIDER = _DEFAULT_LLM_PROVIDER
Config.DEFAULT_LLM_MODEL = _DEFAULT_LLM_MODEL
Config.DEFAULT_LLM_API_KEY = _DEFAULT_LLM_API_KEY

Config.RESEARCHER_PROVIDER = Config._provider_value("RESEARCHER_PROVIDER", Config.DEFAULT_LLM_PROVIDER)
Config.RESEARCHER_MODEL    = Config._model_value("RESEARCHER_MODEL", Config.DEFAULT_LLM_MODEL, Config.RESEARCHER_PROVIDER)
Config.RESEARCHER_API_KEY  = Config._api_key_value("RESEARCHER_API_KEY", Config.DEFAULT_LLM_API_KEY, Config.RESEARCHER_PROVIDER, Config.OPENROUTER_API_KEY)
Config.RESEARCHER_BASE_URL = Config._base_url(Config.RESEARCHER_PROVIDER, Config.OPENROUTER_BASE_URL)

Config.PLANNER_PROVIDER = Config._provider_value("PLANNER_PROVIDER", Config.DEFAULT_LLM_PROVIDER)
Config.PLANNER_MODEL    = Config._model_value("PLANNER_MODEL", Config.DEFAULT_LLM_MODEL, Config.PLANNER_PROVIDER)
Config.PLANNER_API_KEY  = Config._api_key_value("PLANNER_API_KEY", Config.DEFAULT_LLM_API_KEY, Config.PLANNER_PROVIDER, Config.OPENROUTER_API_KEY)
Config.PLANNER_BASE_URL = Config._base_url(Config.PLANNER_PROVIDER, Config.OPENROUTER_BASE_URL)

Config.WRITER_PROVIDER = Config._provider_value("WRITER_PROVIDER", Config.DEFAULT_LLM_PROVIDER)
Config.WRITER_MODEL    = Config._model_value("WRITER_MODEL", Config.DEFAULT_LLM_MODEL, Config.WRITER_PROVIDER)
Config.WRITER_API_KEY  = Config._api_key_value("WRITER_API_KEY", Config.DEFAULT_LLM_API_KEY, Config.WRITER_PROVIDER, Config.OPENROUTER_API_KEY)
Config.WRITER_BASE_URL = Config._base_url(Config.WRITER_PROVIDER, Config.OPENROUTER_BASE_URL)

Config.OPTIMIZER_PROVIDER = Config._provider_value("OPTIMIZER_PROVIDER", Config.DEFAULT_LLM_PROVIDER)
Config.OPTIMIZER_MODEL    = Config._model_value("OPTIMIZER_MODEL", Config.DEFAULT_LLM_MODEL, Config.OPTIMIZER_PROVIDER)
Config.OPTIMIZER_API_KEY  = Config._api_key_value("OPTIMIZER_API_KEY", Config.DEFAULT_LLM_API_KEY, Config.OPTIMIZER_PROVIDER, Config.OPENROUTER_API_KEY)
Config.OPTIMIZER_BASE_URL = Config._base_url(Config.OPTIMIZER_PROVIDER, Config.OPENROUTER_BASE_URL)

Config.QA_PROVIDER = Config._provider_value("QA_PROVIDER", Config.DEFAULT_LLM_PROVIDER)
Config.QA_MODEL    = Config._model_value("QA_MODEL", Config.DEFAULT_LLM_MODEL, Config.QA_PROVIDER)
Config.QA_API_KEY  = Config._api_key_value("QA_API_KEY", Config.DEFAULT_LLM_API_KEY, Config.QA_PROVIDER, Config.OPENROUTER_API_KEY)
Config.QA_BASE_URL = Config._base_url(Config.QA_PROVIDER, Config.OPENROUTER_BASE_URL)

# --- n8n / GEO / AEO Report Agents ---

Config.WEBSITE_DATA_PROVIDER = Config._provider_value("WEBSITE_DATA_PROVIDER", Config.DEFAULT_LLM_PROVIDER)
Config.WEBSITE_DATA_MODEL    = Config._model_value("WEBSITE_DATA_MODEL", Config.DEFAULT_LLM_MODEL, Config.WEBSITE_DATA_PROVIDER)
Config.WEBSITE_DATA_API_KEY  = Config._api_key_value("WEBSITE_DATA_API_KEY", Config.DEFAULT_LLM_API_KEY, Config.WEBSITE_DATA_PROVIDER, Config.OPENROUTER_API_KEY)
Config.WEBSITE_DATA_BASE_URL = Config._base_url(Config.WEBSITE_DATA_PROVIDER, Config.OPENROUTER_BASE_URL)

Config.AEO_AUDIT_PROVIDER = Config._provider_value("AEO_AUDIT_PROVIDER", Config.DEFAULT_LLM_PROVIDER)
Config.AEO_AUDIT_MODEL    = Config._model_value("AEO_AUDIT_MODEL", Config.DEFAULT_LLM_MODEL, Config.AEO_AUDIT_PROVIDER)
Config.AEO_AUDIT_API_KEY  = Config._api_key_value("AEO_AUDIT_API_KEY", Config.DEFAULT_LLM_API_KEY, Config.AEO_AUDIT_PROVIDER, Config.OPENROUTER_API_KEY)
Config.AEO_AUDIT_BASE_URL = Config._base_url(Config.AEO_AUDIT_PROVIDER, Config.OPENROUTER_BASE_URL)

Config.ENHANCED_SCHEMA_PROVIDER = Config._provider_value("ENHANCED_SCHEMA_PROVIDER", Config.DEFAULT_LLM_PROVIDER)
Config.ENHANCED_SCHEMA_MODEL    = Config._model_value("ENHANCED_SCHEMA_MODEL", Config.DEFAULT_LLM_MODEL, Config.ENHANCED_SCHEMA_PROVIDER)
Config.ENHANCED_SCHEMA_API_KEY  = Config._api_key_value("ENHANCED_SCHEMA_API_KEY", Config.DEFAULT_LLM_API_KEY, Config.ENHANCED_SCHEMA_PROVIDER, Config.OPENROUTER_API_KEY)
Config.ENHANCED_SCHEMA_BASE_URL = Config._base_url(Config.ENHANCED_SCHEMA_PROVIDER, Config.OPENROUTER_BASE_URL)

Config.PAIN_POINTS_PROVIDER = Config._provider_value("PAIN_POINTS_PROVIDER", Config.DEFAULT_LLM_PROVIDER)
Config.PAIN_POINTS_MODEL    = Config._model_value("PAIN_POINTS_MODEL", Config.DEFAULT_LLM_MODEL, Config.PAIN_POINTS_PROVIDER)
Config.PAIN_POINTS_API_KEY  = Config._api_key_value("PAIN_POINTS_API_KEY", Config.DEFAULT_LLM_API_KEY, Config.PAIN_POINTS_PROVIDER, Config.OPENROUTER_API_KEY)
Config.PAIN_POINTS_BASE_URL = Config._base_url(Config.PAIN_POINTS_PROVIDER, Config.OPENROUTER_BASE_URL)

Config.FILES_GEN_PROVIDER = Config._provider_value("FILES_GEN_PROVIDER", Config.DEFAULT_LLM_PROVIDER)
Config.FILES_GEN_MODEL    = Config._model_value("FILES_GEN_MODEL", Config.DEFAULT_LLM_MODEL, Config.FILES_GEN_PROVIDER)
Config.FILES_GEN_API_KEY  = Config._api_key_value("FILES_GEN_API_KEY", Config.DEFAULT_LLM_API_KEY, Config.FILES_GEN_PROVIDER, Config.OPENROUTER_API_KEY)
Config.FILES_GEN_BASE_URL = Config._base_url(Config.FILES_GEN_PROVIDER, Config.OPENROUTER_BASE_URL)

