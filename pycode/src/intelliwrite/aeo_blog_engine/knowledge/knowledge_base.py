import logging
import os
from typing import Optional
import traceback
import requests

from agno.vectordb.qdrant import Qdrant
from agno.knowledge.embedder.openai import OpenAIEmbedder
from config.settings import Config
from utils.log_utils import get_logger

LOGGER = get_logger(__name__) # Moved this line up

EMBEDDER_PROVIDER = os.getenv("EMBEDDER_PROVIDER", "auto").lower()


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise RuntimeError(
                "sentence-transformers library is not installed. "
                "Install it with: pip install sentence-transformers"
            )
        self.model = SentenceTransformer(model_name)
        # all-MiniLM-L6-v2 produces 384-dimensional embeddings
        self.dimensions = self.model.get_sentence_embedding_dimension()

    def get_embedding(self, text: str):
        # SentenceTransformer's encode returns a numpy array, convert to list
        return self.model.encode(text).tolist()


class _InMemoryKnowledge:
    """Very small in-memory fallback to keep the pipeline running without Qdrant."""

    def __init__(self):
        docs = []
        kb_path = os.path.join(os.path.dirname(__file__), "docs")
        for root, _, files in os.walk(kb_path):
            for file_name in files:
                if file_name.endswith((".md", ".txt")):
                    file_path = os.path.join(root, file_name)
                    with open(file_path, "r", encoding="utf-8") as handle:
                        docs.append(handle.read())
        self._documents = docs

    def exists(self):
        return True

    def search(self, query: str, limit: int = 3, **_):
        class _Doc:
            def __init__(self, text: str):
                self.content = text

        return [_Doc(text) for text in self._documents[:limit]]


_cached_vector_db: Optional[object] = None
_cached_brand_vector_db: Optional[object] = None


class OpenAICompatEmbedder:
    def __init__(
        self,
        *,
        model_id: str,
        api_key: str,
        base_url: str,
        dimensions: Optional[int] = None,
        extra_headers: Optional[dict] = None,
    ):
        self.model_id = model_id
        self.api_key = api_key
        self.dimensions = dimensions
        self.base_url = base_url.rstrip("/") + "/embeddings"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if extra_headers:
            self.headers.update(extra_headers)

    def get_embedding(self, text: str):
        response = requests.post(
            self.base_url,
            json={"model": self.model_id, "input": text},
            headers=self.headers,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("data"):
            raise ValueError(f"No embedding returned for {self.model_id}: {data}")
        return data["data"][0]["embedding"]


def _use_in_memory_fallback(reason: str):
    LOGGER.warning("Falling back to in-memory knowledge base. Reason: %s", reason)
    if "QDRANT_URL=:memory:" not in reason:
        LOGGER.debug("Detailed error traceback:")
        traceback.print_exc()
    return _InMemoryKnowledge()


def get_knowledge_base():
    """Return Qdrant vector DB, falling back to in-memory storage when necessary."""
    global _cached_vector_db
    if _cached_vector_db:
        return _cached_vector_db

    if (
        not Config.GEMINI_API_KEY
        and not Config.OPENROUTER_API_KEY
        and not Config.OPENAI_API_KEY
        and Config.DEFAULT_LLM_PROVIDER != "ollama"
    ):
        LOGGER.warning(
            "No LLM API keys configured; falling back to in-memory knowledge base."
        )
        _cached_vector_db = _use_in_memory_fallback("Missing LLM API keys")
        return _cached_vector_db

    if Config.QDRANT_URL == ":memory":
        _cached_vector_db = _use_in_memory_fallback("QDRANT_URL=:memory:")
        return _cached_vector_db

    try:
        _cached_vector_db = _build_qdrant(Config.COLLECTION_NAME)
        return _cached_vector_db
    except Exception as exc:
        _cached_vector_db = _use_in_memory_fallback(str(exc))
        return _cached_vector_db


def get_brand_knowledge_base():
    """Return the brand knowledge base collection if available.

    If the configured brand collection does not exist (common in fresh Qdrant projects),
    fall back to the default knowledge base to avoid repeated 404 warnings during .search().
    """

    global _cached_brand_vector_db
    if _cached_brand_vector_db:
        return _cached_brand_vector_db

    if Config.QDRANT_URL == ":memory":
        _cached_brand_vector_db = _use_in_memory_fallback("QDRANT_URL=:memory:")
        return _cached_brand_vector_db

    try:
        candidate = _build_qdrant(Config.BRAND_COLLECTION_NAME)

        # Proactively verify the collection exists to prevent noisy 404s on search.
        if hasattr(candidate, "client"):
            try:
                candidate.client.get_collection(Config.BRAND_COLLECTION_NAME)
            except Exception as exc:
                LOGGER.warning(
                    "Brand KB collection '%s' not found; using default KB instead. (%s)",
                    Config.BRAND_COLLECTION_NAME,
                    exc,
                )
                _cached_brand_vector_db = get_knowledge_base()
                return _cached_brand_vector_db

        _cached_brand_vector_db = candidate
        return _cached_brand_vector_db
    except Exception as exc:
        LOGGER.warning(
            "Brand knowledge base unavailable (%s). Falling back to default KB.", exc
        )
        _cached_brand_vector_db = get_knowledge_base()
        return _cached_brand_vector_db


def _build_qdrant(collection_name: str):
    LOGGER.info(
        "Attempting to connect to Qdrant at %s for collection '%s'...",
        Config.QDRANT_URL,
        collection_name,
    )

    # Pre-check connectivity with a short timeout
    try:
        url = Config.QDRANT_URL.rstrip("/") + "/collections"
        # Skip check for in-memory or special URLs
        if not Config.QDRANT_URL.startswith("http"):
            pass
        else:
            LOGGER.debug("Pinging Qdrant at %s...", url)
            # Use a very short timeout (e.g., 2 seconds) to fail fast
            requests.get(
                url,
                timeout=2,
                headers={"api-key": Config.QDRANT_API_KEY} if Config.QDRANT_API_KEY else None,
            )
            LOGGER.debug("Qdrant is reachable.")
    except Exception as exc:
        LOGGER.warning(
            "Qdrant at %s is unreachable (timeout/error): %s", Config.QDRANT_URL, exc
        )
        raise exc

    try:
        embedder = _select_embedder()
        instance = Qdrant(
            collection=collection_name,
            url=Config.QDRANT_URL,
            api_key=Config.QDRANT_API_KEY,
            embedder=embedder,
        )
        # Attempt a lightweight call to verify connection
        if hasattr(instance, "client"):
            # We already verified connectivity via requests above.
            # Skipping the client.get_collections() call as it can hang indefinitely
            # or cause issues with version compatibility checks.
            LOGGER.debug(
                "Skipping client.get_collections() verification (pre-check passed)."
            )
            LOGGER.info("Successfully connected to Qdrant.")
        return instance
    except Exception as e:
        LOGGER.error("Failed to connect to Qdrant: %s", e)
        raise e


def _select_embedder():
    preference = EMBEDDER_PROVIDER
    provider_order = []

    # 'google' is an alias for 'gemini'
    if preference in ("gemini", "google"):
        provider_order = ["gemini", "openai"]
    elif preference == "ollama":
        provider_order = ["ollama", "openai", "gemini"]
    elif preference == "openai":
        provider_order = ["openai", "gemini"]
    else:  # "auto" or anything else — prefer cloud, skip openrouter (no embeddings API)
        provider_order = ["openai", "gemini", "ollama"]

    LOGGER.info("Selecting embedder with provider order: %s", provider_order)

    for provider in provider_order:
        if provider == "ollama":
            try:
                LOGGER.info("Attempting to load SentenceTransformer for Ollama embeddings...")
                embedder = SentenceTransformerEmbedder("all-MiniLM-L6-v2")
                LOGGER.info("Using SentenceTransformer for embeddings (all-MiniLM-L6-v2).")
                return embedder
            except Exception as e:
                LOGGER.warning("Could not load SentenceTransformer model for Ollama: %s", e)
                continue
        if provider == "openai" and Config.OPENAI_API_KEY:
            LOGGER.info("Using OpenAI embedder: text-embedding-3-small (1536 dims)")
            return OpenAIEmbedder(
                id="text-embedding-3-small",
                api_key=Config.OPENAI_API_KEY,
                dimensions=1536,
            )
        # NOTE: OpenRouter does NOT provide an embeddings API — always skip it.
        if provider == "gemini" and Config.GEMINI_API_KEY:
            # text-embedding-004 produces 768-dimensional vectors
            LOGGER.info("Using Gemini embedder: text-embedding-004 (768 dims)")
            return OpenAICompatEmbedder(
                model_id="models/text-embedding-004",
                api_key=Config.GEMINI_API_KEY,
                base_url=Config.GEMINI_BASE_URL,
                dimensions=768,
            )

    raise ValueError(
        "Unable to initialize embedder. Set EMBEDDER_PROVIDER=gemini or openai and supply the matching API key."
    )
