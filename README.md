# Business Advice Assistant

Beautiful, modular Retrieval-Augmented Generation (RAG) assistant for business planning.

This repository provides:

- A lightweight API-based LLM client (`app/api_llm_service.py`) that uses an
  OpenRouter/OpenAI-compatible chat API for generation.
- A central `LLMClient` wrapper in `app/llm_service.py` that delegates
  generation to the API client and cooperates with a RAG service.
- A SQL → RAG ingestion pipeline (`app/sql_rag_pipeline.py`) that reads
  textual records from SQL, chunks them, computes batched embeddings and
  stores them in a Chroma vector store for retrieval.
- A RAG service helper (`app/rag.py`) that uses HuggingFace embeddings and
  Chroma for vector search.

This README explains how the pieces fit, how to configure them, and gives
examples for ingesting SQL data and running retrieval-augmented generation.

---

## Key Features

- Modular LLM pipeline that can use local transformers or a remote API.
- SQL ingestion pipeline with chunking and batched embeddings to scale to
  large tables.
- Retrieval quality improvements: query-embedding retrieval and metadata
  traceability for retrieved passages.
- Clear fallbacks and lazy imports so modules import cleanly when optional
  dependencies are not installed.

---

## Architecture & Workflow

High level flow:

1. Ingest data into vector store:
   - Use `SQLRAGPipeline.ingest_from_sql()` to read rows from a SQL database,
     split long text into chunks, and add them to a Chroma vector store.
   - Chroma + HuggingFace embeddings compute and persist vector representations.
2. Retrieval:
   - `RAGService` or `SQLRAGPipeline.search()` performs similarity search.
   - Query embedding-based search (preferred) produces higher-quality results.
3. Generation:
   - `LLMClient` (in `app/llm_service.py`) composes prompts that include
     retrieved context and delegates generation to the API client
     (`app/api_llm_service.py`).

Benefits:

- Chunking reduces hallucination risk and keeps context focused.
- Batch embedding reduces memory/compute spikes when indexing large datasets.
- Metadata per chunk provides traceability back to original SQL rows.

---

## Prerequisites

- Python 3.10+
- Recommended (for full functionality):
  - `sqlalchemy`
  - `langchain_chroma` (Chroma vector store binding)
  - `langchain_huggingface` (HuggingFace embeddings)
  - `langchain_text_splitters`

Install project dependencies listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

If you don't need the SQL ingestion or RAG features, you can skip installing
the langchain/chroma packages — the modules are written to fail with clear
errors only when you call the functionality that requires them.

---

## Configuration & Environment Variables

Recommended environment variables (do not commit secrets to source):

- `OPENROUTER_API_KEY` or similar — your OpenRouter/OpenAI-compatible API key.
- `HF_TOKEN` — (optional) HuggingFace Hub token for some embedding models.

The code includes a `Config` dataclass in `app/api_llm_service.py`. For
security, prefer setting the API key via environment variables and updating
the code to read from `os.environ` rather than embedding keys in code.

Example (bash):

```bash
export OPENROUTER_API_KEY="sk-..."
export HF_TOKEN="hf_..."
```

---

## Quickstart — SQL ingestion example

This example ingests textual content stored in a SQLite database and runs a
similarity search.

1. Create a small SQLite database (example):

```bash
python - <<'PY'
import sqlite3
conn = sqlite3.connect('data/example.db')
cur = conn.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, title TEXT, content TEXT)')
cur.execute("INSERT INTO notes (title,content) VALUES (?,?)", ('Market Note','The market size for X is estimated at $1B...'))
conn.commit()
conn.close()
PY
```

2. Index the table into Chroma via the pipeline (example script):

```python
from app.sql_rag_pipeline import SQLRAGPipeline

pipeline = SQLRAGPipeline(persist_directory='chroma_db')

# A simple SELECT returning id and content columns
pipeline.ingest_from_sql(
    connection_string='sqlite:///data/example.db',
    query='SELECT id, content FROM notes',
    id_column='id',
    text_column='content',
    batch_size=100,
    chunk_size=800,
    chunk_overlap=100
)

print(pipeline.search('market size', k=3))
```

Notes:

- Adjust `chunk_size` and `chunk_overlap` to suit the typical length of
  your content. Smaller chunks increase recall but increase number of
  vectors stored.
- `batch_size` controls how many chunks we send to Chroma in each operation.

---

## Quickstart — API LLM generation example

Use the API client wrapper for generation. Prefer to read your API key from
environment variables.

```python
from app.api_llm_service import APIClient, Config

cfg = Config()
# cfg.api_key should be set from env (modify the dataclass or set before init)
client = APIClient(cfg)

result = client.generate('Hello — summarize the business case for X', sys_prompt='You are a helpful business assistant')
print(result)
```

To use this in RAG flows, include retrieved context from the vector store inside
the prompt you send to the LLM. See `app/llm_service.py` for how this repository
composes prompts that combine clarifications and retrieved market context.

---

## Testing & Validation

- Unit tests are not included by default. To validate basic imports:

```bash
python -c "import app.sql_rag_pipeline; import app.llm_service; print('imports OK')"
```

- For end-to-end checks, install `langchain_chroma`, `langchain_huggingface`,
  and ensure `HF_TOKEN` is set if needed, then run the SQL ingestion example
  above.

---

## Troubleshooting

- Module import errors mentioning `langchain_chroma` or
  `langchain_huggingface` mean those optional deps are missing. Install the
  packages or avoid calling the functions that need them.
- If Chroma reports persistence errors, verify `persist_directory` exists and
  is writable.
- If retrieval returns low-quality results, try:
  - Increasing `chunk_size` or decreasing `chunk_overlap`.
  - Using a larger embedding model (change `embedding_model` argument).
  - Increasing the number of retrieved documents `k` when calling `search()`.

---

## Contributing

Contributions welcome. Please open an issue for feature requests or bug
reports. Follow these steps for code contributions:

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/your-feature`.
3. Add tests for your change and update `README.md` as needed.
4. Open a PR describing your changes.

---

## License

This project includes a `LICENSE` file in the repository root — please
refer to it for license terms.

---

## Short Arabic summary

هذا المشروع يوفّر أداة RAG متكاملة لقراءة نصوص من قاعدة بيانات SQL،
فهرستها في Chroma باستخدام تمثيلات متجهية، ثم استخدام هذه الوثائق كملخص
سياقي مع نموذج لغوي لإنتاج خطط أو نصائح تجارية.

For detailed examples, see `app/sql_rag_pipeline.py` and `app/llm_service.py`.
# business_assistant
RAG project for Data Sources for Business Advice Assistant 
