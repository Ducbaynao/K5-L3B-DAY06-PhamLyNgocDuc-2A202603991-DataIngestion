"""Store and search vectors using PostgreSQL + pgvector."""
import json
from pathlib import Path
from typing import Any
from dotenv import dotenv_values
import psycopg

try:
  from .models import Chunk
except ImportError:
  from starter.src.models import Chunk


def get_repo_root() -> Path:
  return Path(__file__).resolve().parent.parent.parent


class PgVectorStore:
  PERMITTED_FILTERS = {"section", "document_id", "page"}

  def __init__(
      self, database_url: str | None = None, dimensions: int = 1536
  ) -> None:
    if database_url is None:
      repo_root = get_repo_root()
      env_path = repo_root / "starter" / ".env"
      env_vals = dotenv_values(str(env_path)) if env_path.exists() else {}
      database_url = env_vals.get("DATABASE_URL")
      if not database_url:
        raise ValueError("DATABASE_URL is not configured in starter/.env")

    self.database_url = database_url
    self.dimensions = dimensions

  def _get_connection(self) -> psycopg.Connection:
    return psycopg.connect(self.database_url)

  def _vector_to_sql_str(self, vec: list[float]) -> str:
    if len(vec) != self.dimensions:
      raise ValueError(
          f"Vector dimension mismatch: expected {self.dimensions}, got"
          f" {len(vec)}"
      )
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"

  def get_existing_dimensions(self) -> int | None:
    """Return dimensions of the existing embedding column if the table exists."""
    with self._get_connection() as conn:
      with conn.cursor() as cur:
        cur.execute("""
                    SELECT a.atttypmod
                    FROM pg_attribute a
                    JOIN pg_class c ON a.attrelid = c.oid
                    JOIN pg_namespace n ON c.relnamespace = n.oid
                    WHERE c.relname = 'document_chunks' 
                      AND a.attname = 'embedding' 
                      AND n.nspname = 'public';
                """)
        row = cur.fetchone()
        if row and row[0] > 0:
          return row[0]
    return None

  def verify_schema(self) -> None:
    """Validate that table exists and vector dimensions match."""
    existing_dim = self.get_existing_dimensions()
    if existing_dim is None:
      raise RuntimeError(
          "Table 'document_chunks' does not exist in database. Run"
          " create_schema() first."
      )
    if existing_dim != self.dimensions:
      raise ValueError(
          f"Database schema mismatch: existing table 'document_chunks' has"
          f" vector dimension {existing_dim}, but configured model requires"
          f" {self.dimensions}. Do not drop the table if it contains data;"
          " resolve configuration or migrate column."
      )

  def create_schema(self) -> None:
    """Create schema and table with vector column, validating existing dimensions."""
    with self._get_connection() as conn:
      with conn.cursor() as cur:
        # Enable pgvector extension
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # Check existing table dimensions if already present
        existing_dim = self.get_existing_dimensions()
        if existing_dim is not None and existing_dim != self.dimensions:
          raise ValueError(
              f"Database schema mismatch: existing table 'document_chunks' has"
              f" vector dimension {existing_dim}, but configured model requires"
              f" {self.dimensions}. Do not drop the table to resolve mismatch."
          )

        # Create chunks table
        cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS document_chunks (
                        strategy VARCHAR(32) NOT NULL,
                        chunk_id VARCHAR(128) NOT NULL,
                        document_id VARCHAR(128) NOT NULL,
                        source VARCHAR(512) NOT NULL,
                        page INTEGER NOT NULL,
                        section VARCHAR(64) NOT NULL,
                        text TEXT NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                        embedding vector({self.dimensions}) NOT NULL,
                        PRIMARY KEY (strategy, chunk_id)
                    );
                """)
        # Indexes for fast lookup and filtering
        cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chunks_strat_doc 
                    ON document_chunks (strategy, document_id);
                """)
        cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chunks_strat_sec 
                    ON document_chunks (strategy, section);
                """)
        # Create index_metadata table to track ingested configurations
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS index_metadata (
                        strategy VARCHAR(32) PRIMARY KEY,
                        model VARCHAR(128) NOT NULL,
                        dimensions INTEGER NOT NULL,
                        pdf_sha256 VARCHAR(64) NOT NULL,
                        corpus_sha256 VARCHAR(64) NOT NULL,
                        chunk_config JSONB NOT NULL DEFAULT '{}'::jsonb,
                        total_chunks INTEGER NOT NULL,
                        run_id VARCHAR(64) NOT NULL,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                """)
      conn.commit()

  def record_index_metadata(self, strategy: str, meta: dict[str, Any]) -> None:
    """Record configuration and checksums of an index after successful ingestion."""
    with self._get_connection() as conn:
      with conn.cursor() as cur:
        cur.execute(
            """
                INSERT INTO index_metadata (
                    strategy, model, dimensions, pdf_sha256, corpus_sha256,
                    chunk_config, total_chunks, run_id, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (strategy) DO UPDATE SET
                    model = EXCLUDED.model,
                    dimensions = EXCLUDED.dimensions,
                    pdf_sha256 = EXCLUDED.pdf_sha256,
                    corpus_sha256 = EXCLUDED.corpus_sha256,
                    chunk_config = EXCLUDED.chunk_config,
                    total_chunks = EXCLUDED.total_chunks,
                    run_id = EXCLUDED.run_id,
                    updated_at = CURRENT_TIMESTAMP;
            """,
            (
                strategy,
                meta["model"],
                meta["dimensions"],
                meta["pdf_sha256"],
                meta["corpus_sha256"],
                json.dumps(meta["chunk_config"], ensure_ascii=False),
                meta["total_chunks"],
                meta["run_id"],
            ),
        )
      conn.commit()

  def get_index_metadata(self, strategy: str) -> dict[str, Any] | None:
    """Retrieve recorded index configuration for a strategy."""
    with self._get_connection() as conn:
      with conn.cursor() as cur:
        cur.execute(
            """
                SELECT strategy, model, dimensions, pdf_sha256, corpus_sha256,
                       chunk_config, total_chunks, run_id, updated_at
                FROM index_metadata
                WHERE strategy = %s;
            """,
            (strategy,),
        )
        row = cur.fetchone()
        if row:
          return {
              "strategy": row[0],
              "model": row[1],
              "dimensions": row[2],
              "pdf_sha256": row[3],
              "corpus_sha256": row[4],
              "chunk_config": row[5] if isinstance(row[5], dict) else json.loads(row[5]),
              "total_chunks": row[6],
              "run_id": row[7],
              "updated_at": str(row[8]),
          }
    return None


  def upsert(
      self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]
  ) -> None:
    """Idempotently insert or update chunks for a strategy within a transaction.

    Obsolete chunks for the same document in this strategy are pruned.
    """
    if len(chunks) != len(vectors):
      raise ValueError(
          f"Length mismatch: {len(chunks)} chunks vs {len(vectors)} vectors"
      )
    if not chunks:
      return

    self.verify_schema()

    # Group by document_id to prune per-document
    docs_touched = set(c.document_id for c in chunks)
    current_ids = [c.chunk_id for c in chunks]

    with self._get_connection() as conn:
      with conn.cursor() as cur:
        # 1. Prune obsolete chunks for these documents under this strategy
        for doc_id in docs_touched:
          cur.execute(
              """
                        DELETE FROM document_chunks
                        WHERE strategy = %s 
                          AND document_id = %s 
                          AND chunk_id != ALL(%s);
                    """,
              (strategy, doc_id, current_ids),
          )

        # 2. Upsert current chunks
        for chunk, vec in zip(chunks, vectors):
          vec_str = self._vector_to_sql_str(vec)
          section = chunk.metadata.get("section", "")
          meta_json = json.dumps(chunk.metadata, ensure_ascii=False)

          cur.execute(
              """
                        INSERT INTO document_chunks (
                            strategy, chunk_id, document_id, source, 
                            page, section, text, metadata, embedding
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::vector
                        )
                        ON CONFLICT (strategy, chunk_id) DO UPDATE SET
                            document_id = EXCLUDED.document_id,
                            source = EXCLUDED.source,
                            page = EXCLUDED.page,
                            section = EXCLUDED.section,
                            text = EXCLUDED.text,
                            metadata = EXCLUDED.metadata,
                            embedding = EXCLUDED.embedding;
                    """,
              (
                  strategy,
                  chunk.chunk_id,
                  chunk.document_id,
                  chunk.source,
                  chunk.page,
                  section,
                  chunk.text,
                  meta_json,
                  vec_str,
              ),
          )
      conn.commit()

  def search(
      self,
      strategy: str,
      query_vector: list[float],
      top_k: int = 3,
      filters: dict[str, Any] | None = None,
  ) -> list[dict[str, Any]]:
    """Exact cosine top-k search with parameterized metadata filters and stable secondary sort."""
    if len(query_vector) != self.dimensions:
      raise ValueError(
          f"Query vector dimensions mismatch: expected {self.dimensions}, got"
          f" {len(query_vector)}"
      )

    vec_str = self._vector_to_sql_str(query_vector)

    sql_parts = [
        """
            SELECT 
                chunk_id, document_id, source, page, section, text, metadata,
                (embedding <=> %s::vector) AS distance,
                (1.0 - (embedding <=> %s::vector)) AS similarity
            FROM document_chunks
            WHERE strategy = %s
        """
    ]
    params: list[Any] = [vec_str, vec_str, strategy]

    if filters:
      for key, val in filters.items():
        if key not in self.PERMITTED_FILTERS:
          raise ValueError(
              f"Filter field '{key}' is not in permitted fields:"
              f" {self.PERMITTED_FILTERS}"
          )
        if key in ("section", "document_id"):
          sql_parts.append(f"AND {key} = %s")
          params.append(val)
        elif key == "page":
          sql_parts.append("AND page = %s")
          params.append(int(val))

    # Stable secondary sort: chunk_id ASC
    sql_parts.append("ORDER BY distance ASC, chunk_id ASC LIMIT %s;")
    params.append(top_k)

    full_sql = " ".join(sql_parts)

    hits: list[dict[str, Any]] = []
    with self._get_connection() as conn:
      with conn.cursor() as cur:
        cur.execute(full_sql, params)
        rows = cur.fetchall()
        for row in rows:
          hits.append({
              "chunk_id": row[0],
              "document_id": row[1],
              "source": row[2],
              "page": row[3],
              "section": row[4],
              "text": row[5],
              "metadata": row[6],
              "distance": float(row[7]),
              "score": float(row[8]),  # cosine similarity
          })
    return hits

  def count_chunks(self, strategy: str) -> int:
    """Return count of chunks stored for a strategy."""
    with self._get_connection() as conn:
      with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM document_chunks WHERE strategy = %s;",
            (strategy,),
        )
        res = cur.fetchone()
        return res[0] if res else 0
