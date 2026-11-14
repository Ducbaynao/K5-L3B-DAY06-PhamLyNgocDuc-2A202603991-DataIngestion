"""OpenAI embedding integration with caching and bounded retries."""
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Protocol
from dotenv import dotenv_values
from openai import APIConnectionError, InternalServerError, OpenAI, RateLimitError


def get_repo_root() -> Path:
  return Path(__file__).resolve().parent.parent.parent


class Embedder(Protocol):
  model_name: str
  dimensions: int

  def embed_documents(self, texts: list[str]) -> list[list[float]]:
    ...

  def embed_query(self, question: str) -> list[float]:
    ...


class OpenAIEmbedder:
  """OpenAI Embeddings client adhering to the Embedder protocol."""

  KNOWN_DIMENSIONS: dict[str, int] = {
      "text-embedding-3-small": 1536,
      "text-embedding-3-large": 3072,
      "text-embedding-ada-002": 1536,
  }

  def __init__(
      self,
      model_name: str | None = None,
      env_path: Path | None = None,
      cache_db_path: Path | None = None,
      batch_size: int = 128,
      max_retries: int = 3,
  ) -> None:
    repo_root = get_repo_root()
    if env_path is None:
      env_path = repo_root / "starter" / ".env"

    env_vals = dotenv_values(str(env_path)) if env_path.exists() else {}

    # 1. Validate API Key without printing or logging it
    api_key = env_vals.get("OPENAI_API_KEY") or ""
    if not api_key or not api_key.strip():
      raise ValueError(
          "OPENAI_API_KEY is not configured or empty in starter/.env. Please"
          " set a valid API key."
      )
    self._api_key = api_key.strip()

    # 2. Validate Model Name
    configured_model = model_name or env_vals.get("EMBEDDING_MODEL")
    if not configured_model or not configured_model.strip():
      raise ValueError(
          "EMBEDDING_MODEL is not configured or empty in starter/.env."
      )
    self.model_name = configured_model.strip()

    if self.model_name not in self.KNOWN_DIMENSIONS:
      raise ValueError(
          f"Unsupported embedding model: '{self.model_name}'. Supported"
          f" models: {list(self.KNOWN_DIMENSIONS.keys())}"
      )
    self.dimensions = self.KNOWN_DIMENSIONS[self.model_name]

    self.batch_size = batch_size
    self.max_retries = max_retries

    # Usage and Cache Statistics
    self.stats: dict[str, int] = {
        "api_calls": 0,
        "prompt_tokens": 0,
        "total_tokens": 0,
        "cache_hits": 0,
        "cache_misses": 0,
    }

    # 3. Setup local cache
    if cache_db_path is None:
      cache_dir = repo_root / "starter" / ".cache"
      cache_dir.mkdir(parents=True, exist_ok=True)
      cache_db_path = cache_dir / "embeddings_cache.sqlite"
    self.cache_db_path = cache_db_path
    self._init_cache()

    # Set max_retries=0 on client to prevent uncontrolled nested retries
    self._client = OpenAI(api_key=self._api_key, max_retries=0)

  def reset_stats(self) -> None:
    """Reset API and cache usage statistics."""
    self.stats = {
        "api_calls": 0,
        "prompt_tokens": 0,
        "total_tokens": 0,
        "cache_hits": 0,
        "cache_misses": 0,
    }

  def get_stats(self) -> dict[str, int]:
    """Return a copy of the current usage and cache statistics."""
    return dict(self.stats)

  def _init_cache(self) -> None:
    self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(self.cache_db_path) as conn:
      conn.execute("""
                CREATE TABLE IF NOT EXISTS embedding_cache (
                    model TEXT NOT NULL,
                    dimensions INTEGER NOT NULL,
                    text_hash TEXT NOT NULL,
                    vector_json TEXT NOT NULL,
                    PRIMARY KEY (model, dimensions, text_hash)
                )
            """)
      conn.commit()

  def _hash_text(self, text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

  def _get_cached_vector(self, text: str) -> list[float] | None:
    text_hash = self._hash_text(text)
    with sqlite3.connect(self.cache_db_path) as conn:
      cur = conn.cursor()
      cur.execute(
          """
                SELECT vector_json FROM embedding_cache
                WHERE model = ? AND dimensions = ? AND text_hash = ?
            """,
          (self.model_name, self.dimensions, text_hash),
      )
      row = cur.fetchone()
      if row:
        vec = json.loads(row[0])
        if len(vec) == self.dimensions:
          self.stats["cache_hits"] += 1
          return vec
    self.stats["cache_misses"] += 1
    return None

  def _save_cached_vectors(self, texts: list[str], vectors: list[list[float]]) -> None:
    with sqlite3.connect(self.cache_db_path) as conn:
      for text, vector in zip(texts, vectors):
        if len(vector) != self.dimensions:
          continue
        text_hash = self._hash_text(text)
        conn.execute(
            """
                    INSERT OR REPLACE INTO embedding_cache (model, dimensions, text_hash, vector_json)
                    VALUES (?, ?, ?, ?)
                """,
            (self.model_name, self.dimensions, text_hash, json.dumps(vector)),
        )
      conn.commit()

  def _call_api_with_retry(self, batch: list[str]) -> list[list[float]]:
    """Call OpenAI API with bounded retries and strict dimension validation."""
    for attempt in range(1, self.max_retries + 1):
      try:
        response = self._client.embeddings.create(
            model=self.model_name,
            input=batch,
        )
        self.stats["api_calls"] += 1
        if hasattr(response, "usage") and response.usage:
          self.stats["prompt_tokens"] += response.usage.prompt_tokens or 0
          self.stats["total_tokens"] += response.usage.total_tokens or 0

        vectors = [item.embedding for item in response.data]

        # Strict validation: vector count must match batch count exactly
        if len(vectors) != len(batch):
          raise ValueError(
              f"OpenAI API returned {len(vectors)} vectors for {len(batch)}"
              " inputs"
          )

        # Strict validation: every vector dimension must match self.dimensions
        for idx, vec in enumerate(vectors):
          if len(vec) != self.dimensions:
            raise ValueError(
                f"Returned vector dimension mismatch at index {idx}: expected"
                f" {self.dimensions}, got {len(vec)}"
            )

        return vectors
      except (RateLimitError, APIConnectionError, InternalServerError) as e:
        if attempt == self.max_retries:
          raise RuntimeError(
              f"OpenAI API failed after {self.max_retries} attempts: {type(e).__name__}"
          ) from e
        sleep_secs = 2**attempt
        time.sleep(sleep_secs)
      except Exception as e:
        if isinstance(e, ValueError):
          raise
        raise RuntimeError(f"OpenAI embedding call failed: {type(e).__name__}: {e}") from e
    raise RuntimeError("OpenAI embedding call failed: exhausted retries")

  def embed_documents(self, texts: list[str]) -> list[list[float]]:
    """Embed document texts maintaining strict 1:1 order without dropping or truncating."""
    if not texts:
      return []

    results: list[list[float] | None] = [self._get_cached_vector(t) for t in texts]
    missing_indices = [i for i, r in enumerate(results) if r is None]

    if missing_indices:
      missing_texts = [texts[i] for i in missing_indices]
      for b_start in range(0, len(missing_texts), self.batch_size):
        b_end = min(b_start + self.batch_size, len(missing_texts))
        batch = missing_texts[b_start:b_end]
        vectors = self._call_api_with_retry(batch)
        self._save_cached_vectors(batch, vectors)
        for offset, vec in enumerate(vectors):
          orig_idx = missing_indices[b_start + offset]
          results[orig_idx] = vec

    # Final guarantee: exactly len(texts) vectors, non-null, exact dimensions
    final_vectors: list[list[float]] = []
    for idx, vec in enumerate(results):
      if vec is None:
        raise ValueError(
            f"Embedding failed: missing vector for input at index {idx}"
        )
      if len(vec) != self.dimensions:
        raise ValueError(
            f"Embedding failed: vector at index {idx} has dimension {len(vec)}"
            f" != {self.dimensions}"
        )
      final_vectors.append(vec)

    return final_vectors

  def embed_query(self, question: str) -> list[float]:
    """Embed single query text."""
    cached = self._get_cached_vector(question)
    if cached is not None:
      return cached
    vectors = self._call_api_with_retry([question])
    self._save_cached_vectors([question], vectors)
    return vectors[0]


class MyEmbedder(OpenAIEmbedder):
  """Alias satisfying the starter contract."""

  def __init__(self, model_name: str | None = None) -> None:
    super().__init__(model_name=model_name)
