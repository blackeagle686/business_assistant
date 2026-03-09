"""SQL -> RAG pipeline

Provides a small utility to ingest textual data from a SQL database into a
Chroma vector-store using HuggingFace embeddings, and to run similarity search
for retrieval-augmented generation (RAG).

This module performs lazy imports so that importing it does not require heavy
dependencies at module import time. If dependencies are missing, methods will
raise informative errors.

Example usage:
    from app.sql_rag_pipeline import SQLRAGPipeline

    pipeline = SQLRAGPipeline(persist_directory='chroma_db')
    pipeline.ingest_from_sql('sqlite:///data/my.db', 'SELECT id, content FROM notes', id_column='id', text_column='content')
    print(pipeline.search('market sizing', k=5))
"""
from typing import List, Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)

# Top-level optional imports so callers get fast import failures with clear
# diagnostics instead of import-time errors deep inside methods.
try:
    from langchain_chroma import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings
    _HAS_LANGCHAIN = True
except Exception:
    Chroma = None
    HuggingFaceEmbeddings = None
    _HAS_LANGCHAIN = False

try:
    from sqlalchemy import create_engine, text
    _HAS_SQLALCHEMY = True
except Exception:
    create_engine = None
    text = None
    _HAS_SQLALCHEMY = False

# ---------------------------------------------------------------------------
# Explanatory comments / purpose
# ---------------------------------------------------------------------------
# This module provides `SQLRAGPipeline` — a small pipeline that reads textual
# content from a SQL database, splits long texts into chunks, computes
# vector embeddings for chunks (via HuggingFace embeddings), stores them in a
# Chroma vector store, and exposes a `search()` method to retrieve relevant
# passages. Retrieval uses query embeddings when possible for higher quality.
#
# Notes on design decisions:
# - Optional heavy dependencies (langchain/chroma, sqlalchemy, text-splitter)
#   are imported at module level but handled gracefully with flags so the
#   module can still be imported in environments missing these packages.
# - Chunking and batch ingestion help with memory usage and ensure embeddings
#   are computed in efficient batches.
# - Metadata stored per chunk includes source and chunk index to trace
#   results back to the original SQL row.
#
# شرح مختصر بالعربية:
# هذا الملف يوفّر خط أنابيب (Pipeline) لقراءة نصوص من قاعدة بيانات SQL،
# تقسيم النصوص الطويلة إلى قطع (chunks)، توليد تمثيلات متجهية (embeddings)
# باستخدام نماذج HuggingFace، وتخزينها في قاعدة بيانات متجهية (Chroma).
# عند البحث، يتم استخدام التمثيل المتجهي للاستعلام للحصول على نتائج أدق.
# ---------------------------------------------------------------------------

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    _HAS_TEXT_SPLITTER = True
except Exception:
    RecursiveCharacterTextSplitter = None
    _HAS_TEXT_SPLITTER = False


class SQLRAGPipeline:
    def __init__(self, persist_directory: str = "chroma_db", embedding_model: str = "all-MiniLM-L6-v2"):
        """Create pipeline instance. Actual heavy libraries are imported lazily.

        Args:
            persist_directory: directory where Chroma will persist its DB.
            embedding_model: name of the sentence-transformers model to use.
        """
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model
        self._vector_store = None
        self._embedding_function = None
        # default text splitter params
        self.default_chunk_size = 1000
        self.default_chunk_overlap = 200
        # ---------------------------
        # Important: initialization notes
        # - `persist_directory` defines where Chroma will persist its files.
        # - `embedding_model` controls which sentence-transformers model is used
        #   to compute embeddings. Default is a lightweight model suitable for
        #   many retrieval tasks.
        # - We defer creating the actual Chroma collection and embedding
        #   function until the first ingestion or search to avoid requiring
        #   heavy libraries at import time.
        # ---------------------------

    def _ensure_vector_store(self):
        if not _HAS_LANGCHAIN:
            raise RuntimeError(
                "Missing langchain/chroma embedding libraries. Install required deps: langchain_chroma, langchain_huggingface"
            )

        if self._vector_store is None or self._embedding_function is None:
            # set HF token if present in env
            if os.getenv("HF_TOKEN"):
                os.environ["HUGGINGFACEHUB_API_TOKEN"] = os.environ.get("HF_TOKEN")

            self._embedding_function = HuggingFaceEmbeddings(model_name=self.embedding_model)
            self._vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self._embedding_function,
            )
            # ---------------------------
            # Notes:
            # - `HuggingFaceEmbeddings` provides `embed_documents` and sometimes
            #   `embed_query`. These are used to compute embeddings for chunks
            #   and for queries respectively.
            # - `Chroma` is configured to use the provided embedding function so
            #   when we call `add_documents` Chroma will compute/store embeddings
            #   automatically (depending on the Chroma binding implementation).
            # ---------------------------

    def ingest_from_sql(self, connection_string: str, query: str, id_column: Optional[str] = None, text_column: str = "content", batch_size: int = 500, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None):
        """Ingest rows from SQL query into the vector store.

        The function reads rows from the given SQL connection string using
        SQLAlchemy (imported lazily). Each row's `text_column` is used as the
        document content; `id_column` (if provided) is used in metadata for source.

        Args:
            connection_string: SQLAlchemy connection string (eg. 'sqlite:///db.db').
            query: SQL query string to select rows (should include text column).
            id_column: optional column name to use as identifier in metadata.
            text_column: column name that contains the textual content.
            batch_size: number of documents to add per batch.
        """
        # Validate required SQL dependency
        if not _HAS_SQLALCHEMY:
            raise RuntimeError("SQL ingestion requires SQLAlchemy. Please install sqlalchemy.")

        # Ensure Chroma + embeddings are initialized (lazy initialization)
        self._ensure_vector_store()

        # Prepare text splitter settings. Chunking reduces the chance of
        # truncation and improves retrieval granularity. If the splitter
        # library is not available we fall back to storing the whole text as
        # a single chunk.
        if chunk_size is None:
            chunk_size = self.default_chunk_size
        if chunk_overlap is None:
            chunk_overlap = self.default_chunk_overlap

        if _HAS_TEXT_SPLITTER:
            splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        else:
            splitter = None

        engine = create_engine(connection_string)

        with engine.connect() as conn:
            result = conn.execute(text(query))

            docs = []
            for row in result:
                try:
                    # SQLAlchemy Row objects expose a mapping interface
                    content = row[text_column] if text_column in row._mapping else None
                except Exception:
                    # row might be a tuple-like; try by attribute or index
                    content = None
                    if hasattr(row, text_column):
                        content = getattr(row, text_column)
                    else:
                        try:
                            # fallback: if only one column selected use it
                            content = list(row._mapping.values())[0]
                        except Exception:
                            content = None

                if content is None:
                    logger.debug("Skipping row without text column: %s", row)
                    continue

                # Create chunks from the row content. We store metadata for each
                # chunk so we can trace results back to the original SQL row and
                # chunk index. This is useful when presenting retrieved passages
                # to users.
                if splitter:
                    try:
                        chunks = splitter.split_text(str(content))
                    except Exception:
                        # If text-splitter fails for any reason, fall back to
                        # treating the entire content as a single chunk.
                        chunks = [str(content)]
                else:
                    chunks = [str(content)]

                for idx, chunk in enumerate(chunks):
                    # Assemble metadata for traceability
                    metadata: Dict[str, Any] = {}
                    if id_column and id_column in row._mapping:
                        metadata["source"] = f"sql:{row._mapping[id_column]}"
                        metadata["row_id"] = row._mapping[id_column]
                    else:
                        metadata["source"] = "sql:unknown"
                    metadata["chunk_index"] = idx

                    docs.append({"page_content": chunk, "metadata": metadata})

                    # When we reach the batch size threshold, push a batch to
                    # the vector store. This keeps memory usage bounded and
                    # allows Chroma/embeddings to process in batches.
                    if len(docs) >= batch_size:
                        self._vector_store.add_documents(docs)
                        logger.info("Ingested %d documents into vector store", len(docs))
                        docs = []

            if docs:
                self._vector_store.add_documents(docs)
                logger.info("Ingested final %d documents into vector store", len(docs))

    def _embed_query(self, query: str):
        """Return embedding for query using embedding function.

        Tries to use `embed_query` if available, otherwise falls back to
        `embed_documents([query])[0]`.
        """
        if not self._embedding_function:
            raise RuntimeError("Embedding function not initialized")

        # Use the library-provided `embed_query` when available because it
        # may apply query-specific optimizations. Otherwise fall back to
        # computing document embeddings for a single-item list and return the
        # first result.
        if hasattr(self._embedding_function, "embed_query"):
            return self._embedding_function.embed_query(query)

        emb = self._embedding_function.embed_documents([query])
        return emb[0]

    def search(self, query: str, k: int = 3) -> str:
        """Run a similarity search and return a combined context string.

        Returns a string composed of the top `k` documents including their
        source metadata and content, separated by blank lines.
        """
        self._ensure_vector_store()

        # We attempt a higher-quality vector search by computing the query
        # embedding and passing it to the vector store. Some Chroma bindings
        # provide `similarity_search_by_vector` which accepts a raw vector.
        # If unavailable, we fall back to `similarity_search` which may accept
        # a text query and handle embedding internally.
        results = None
        if _HAS_LANGCHAIN and self._embedding_function:
            try:
                q_emb = self._embed_query(query)
                try:
                    results = self._vector_store.similarity_search_by_vector(q_emb, k=k)
                except Exception:
                    results = self._vector_store.similarity_search(query, k=k)
            except Exception:
                # If query embedding fails, use the plain text search
                results = self._vector_store.similarity_search(query, k=k)
        else:
            # If embeddings or langchain are not available, attempt plain text
            # similarity search (implementation dependent).
            results = self._vector_store.similarity_search(query, k=k)
        context = "\n\n".join([f"Source: {doc.metadata.get('source', 'unknown')}\nContent: {doc.page_content}" for doc in results])
        return context

    def reset_collection(self):
        """Delete all persisted documents in the Chroma collection.

        NOTE: This will remove the persisted DB files. Use with care.
        """
        self._ensure_vector_store()
        try:
            # Preferred: use the Chroma API to delete the collection if available
            self._vector_store.delete_collection()
        except Exception:
            # Some Chroma bindings expose a lower-level collection object; if
            # present, truncate it to remove all documents. This is destructive
            # and irreversible for persisted stores.
            try:
                self._vector_store._collection.truncate()
            except Exception:
                logger.warning("Unable to fully reset Chroma collection with current binding")


__all__ = ["SQLRAGPipeline"]


# ---------------------------------------------------------------------------
# Pipeline workflow and benefits (English + Arabic)
# ---------------------------------------------------------------------------
# Workflow (what happens when you use this pipeline):
# 1. Create `SQLRAGPipeline` with a `persist_directory` and optional
#    `embedding_model`.
# 2. Call `ingest_from_sql(connection_string, query, ...)`:
#    - The pipeline reads rows from your SQL database using SQLAlchemy.
#    - Each row's text is split into smaller chunks (configurable chunk_size
#      and chunk_overlap).
#    - Each chunk is given metadata (source, row id, chunk index) and
#      collected into batches.
#    - Batches are added to the Chroma vector store; embeddings are computed
#      (via HuggingFace embeddings) and stored alongside chunks.
# 3. Call `search(query, k)` to retrieve the top-k most relevant chunks:
#    - The pipeline attempts to compute a query embedding and run a
#      vector-based similarity search for better retrieval quality.
#    - It returns a concatenated context string with sources and content.
#
# Benefits:
# - Incremental + batched ingestion avoids memory spikes and allows large
#   datasets to be indexed.
# - Chunking improves recall and helps the LLM avoid hallucinating by
#   providing smaller, more focused passages as context.
# - Metadata per chunk makes retrieved results traceable back to their
#   origin in your SQL data.
# - Query-embedding based search improves relevance compared to raw text
#   matching.
#
# سير العمل (بالعربية):
# 1. أنشئ `SQLRAGPipeline` وحدد مجلد التخزين واسم نموذج الـ embedding.
# 2. استعمل `ingest_from_sql` لقراءة الصفوف من قاعدة البيانات:
#    - يُقسّم النص لكل سطر إلى قطع صغيرة (chunks).
#    - تُحسب تمثيلات متجهية لكل قطعة وتُخزن في Chroma مع بيانات وصفية.
# 3. استعمل `search` للحصول على أفضل المقاطع ذات الصلة بالاستعلام.
#
# ملاحظات:
# - تأكد من تنصيب الحزم المطلوبة (`sqlalchemy`, `langchain_chroma`,
#   `langchain_huggingface`, `langchain_text_splitters`) عند تشغيل
#   وظائف الفهرسة أو البحث.
# - يمكنك تعديل `chunk_size`, `chunk_overlap` و`batch_size` لموازنة الدقة
#   والأداء حسب بياناتك.
# ---------------------------------------------------------------------------
