from __future__ import annotations

import hashlib
import math
import re
from os import getenv
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)

EMBEDDING_PROVIDER_ENV = "EMBEDDING_PROVIDER"
LOCAL_EMBEDDING_MODEL = getenv("LOCAL_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
OPENAI_EMBEDDING_MODEL = getenv("OPENAI_EMBEDDING_MODEL", getenv("JINA_EMBEDDING_MODEL", "text-embedding-3-small"))
OPENAI_API_KEY = getenv("OPENAI_API_KEY", getenv("JINA_EMBEDDING_KEY", ""))
OPENAI_BASE_URL = getenv("OPENAI_BASE_URL", getenv("JINA_EMBEDDING_URL", ""))
OPENAI_EMBEDDING_DIM = int(getenv("OPENAI_EMBEDDING_DIM", getenv("JINA_EMBEDDING_DIM", "1536")))
MOCK_EMBEDDING_DIM = 64


def _normalize(vector: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        return vector
    return [value / magnitude for value in vector]


def _stable_bucket(token: str, dim: int) -> tuple[int, float]:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    index = int.from_bytes(digest[:4], "big") % dim
    sign = 1.0 if digest[4] % 2 == 0 else -1.0
    weight = 1.0 + (digest[5] / 255.0)
    return index, sign * weight


def _mock_embed(text: str, dim: int = MOCK_EMBEDDING_DIM) -> list[float]:
    """
    Deterministic lightweight embedding for tests and offline experiments.

    The function hashes word tokens and character trigrams into a fixed-size
    vector, then L2-normalizes the result. Similar texts that share vocabulary
    land closer together without requiring any external dependency or API key.
    """

    cleaned = text.strip().lower()
    if not cleaned:
        return [0.0] * dim

    vector = [0.0] * dim
    tokens = re.findall(r"\w+", cleaned, flags=re.UNICODE)
    if not tokens:
        tokens = [cleaned]

    for token in tokens:
        index, weight = _stable_bucket(token, dim)
        vector[index] += weight

        if len(token) >= 3:
            for start in range(len(token) - 2):
                trigram = token[start : start + 3]
                trigram_index, trigram_weight = _stable_bucket(f"tri:{trigram}", dim)
                vector[trigram_index] += trigram_weight * 0.35

    return _normalize(vector)


class MockEmbedder:
    """Small deterministic embedder used by the test suite and manual demos."""

    def __init__(self, dim: int = MOCK_EMBEDDING_DIM) -> None:
        self.dim = dim
        self._backend_name = f"mock-{dim}d"

    def __call__(self, text: str) -> list[float]:
        return _mock_embed(text, dim=self.dim)


class LocalEmbedder:
    """SentenceTransformer wrapper for optional local embeddings."""

    def __init__(self, model_name: str | None = None) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is not installed. Run `pip install sentence-transformers` "
                "to use LocalEmbedder."
            ) from exc

        self.model_name = (model_name or LOCAL_EMBEDDING_MODEL).strip()
        if not self.model_name:
            raise ValueError("Missing local embedding model name.")

        self.model = SentenceTransformer(self.model_name)
        self._backend_name = self.model_name

    def __call__(self, text: str) -> list[float]:
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("Input text for embedding must not be empty.")

        embedding = self.model.encode(cleaned, normalize_embeddings=True)
        return [float(value) for value in embedding]


class OpenAIEmbedder:
    """OpenAI-compatible embeddings client for OpenAI or Jina-style APIs."""

    def __init__(
        self,
        model_name: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "openai is not installed. Run `pip install openai` to use OpenAIEmbedder."
            ) from exc

        self.model_name = (model_name or OPENAI_EMBEDDING_MODEL or "").strip()
        self.api_key = (api_key or OPENAI_API_KEY or "").strip()
        self.base_url = (base_url or OPENAI_BASE_URL or "").strip()
        self._backend_name = self.model_name or "openai-compatible"

        self._validate_config()
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self.client = OpenAI(**client_kwargs)

    def __call__(self, text: str) -> list[float]:
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("Input text for embedding must not be empty.")

        response = self.client.embeddings.create(model=self.model_name, input=cleaned)
        if not response.data:
            raise ValueError("Embedding API returned no data.")

        embedding = [float(value) for value in response.data[0].embedding]
        if OPENAI_EMBEDDING_DIM and len(embedding) != OPENAI_EMBEDDING_DIM and OPENAI_BASE_URL:
            raise ValueError(
                f"Unexpected embedding size: got {len(embedding)}, expected {OPENAI_EMBEDDING_DIM}."
            )
        return embedding

    def _validate_config(self) -> None:
        if not self.model_name:
            raise ValueError(
                "Missing embedding model name. Set OPENAI_EMBEDDING_MODEL or JINA_EMBEDDING_MODEL."
            )
        if not self.api_key:
            raise ValueError(
                "Missing API key. Set OPENAI_API_KEY or JINA_EMBEDDING_KEY."
            )
