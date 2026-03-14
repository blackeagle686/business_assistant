# 💼 Business Advisor AI

<p align="center">
  <img src="https://img.icons8.com/illustrations/external-tulpahn-outline-color-tulpahn/100/external-business-strategy-business-and-finance-tulpahn-outline-color-tulpahn.png" alt="Business Advisor Logo" width="120" />
</p>

<p align="center">
  <strong>Advanced RAG-powered business planning and market research assistant.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LangChain-Project-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white" alt="LangChain" />
  <img src="https://img.shields.io/badge/ChromaDB-VectorStore-00C4CC?style=for-the-badge" alt="ChromaDB" />
  <img src="https://img.shields.io/badge/Hugging_Face-Models-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black" alt="Hugging Face" />
  <img src="https://img.shields.io/badge/OpenRouter-LLM-000000?style=for-the-badge" alt="OpenRouter" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
</p>

---

## 🚀 About the Project

**Business Advisor AI** is a modular Retrieval-Augmented Generation (RAG) system designed to provide data-driven business advice and strategic planning. By grounding LLM reasoning in industry-specific data (SQL tables, PDFs, and market reports), it delivers accurate, non-hallucinated insights for new ventures.

### ✨ Key Features

-   **🔍 Multi-Source RAG**: Ingests data from SQL databases and PDFs into a Chroma vector store.
-   **🤖 Intelligent Reasoning**: Powered by Qwen (via OpenRouter/OpenAI API) for high-quality logic.
-   **📈 KPI Frameworks**: Automatically generates industry-specific metrics and measurement strategies.
-   **💬 Interactive Analysis**: Chat with the assistant to refine specific sections of your business plan.
-   **🛠️ Modular Design**: Easily swap LLM providers, embedding models, or vector databases.

---

## 🛠️ Tech Stack

-   **Core Interface**: [FastAPI](https://fastapi.tiangolo.com/) (Async API backend)
-   **LLM Orchestration**: [LangChain](https://www.langchain.com/)
-   **Vector Database**: [ChromaDB](https://www.trychroma.com/)
-   **Embeddings**: [Hugging Face](https://huggingface.co/) (Sentence-Transformers)
-   **LLM Provider**: [OpenRouter](https://openrouter.ai/) / [OpenAI](https://openai.com/)
-   **Frontend**: HTML5, CSS3 (Modern Glassmorphism), Bootstrap 5

---

## 🏗️ Architecture & Workflow

The system follows a classic RAG architecture optimized for business data ingestion and retrieval.

### Workflow Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant A as FastAPI App
    participant V as Vector Store (Chroma)
    participant L as LLM Service (OpenRouter)
    
    U->>A: Submit Business Idea
    A->>L: Generate Clarification Questions
    L-->>A: Questions
    A-->>U: Show Questions
    
    U->>A: Submit Answers
    A->>V: Search Relevant Market Context
    V-->>A: Retrieved Snippets
    A->>L: Generate Business Plan (Idea + Answers + Context)
    L-->>A: Structured Plan
    A-->>U: Display Dashboard & Plan
```

1.  **Ingestion**: `SQLRAGPipeline` reads rows from SQL, chunks text, and stores embeddings in Chroma.
2.  **Interaction**: User submits an idea; the system asks clarifying questions to narrow scope.
3.  **Retrieval**: The `RAGService` performs similarity search using HuggingFace embeddings.
4.  **Generation**: The `LLMClient` composes a prompt with retrieved context and user answers, then calls the API.

---

## 🏁 Quickstart

### 1. Installation

```bash
git clone https://github.com/your-username/business-advisor-ai.git
cd business-advisor-ai
pip install -r requirements.txt
```

### 2. Environment Setup

Create a `.env` file in the root directory:

```env
OPENROUTER_API_KEY=your_key_here
HF_TOKEN=your_token_here (optional)
```

### 3. Run the Application

```bash
uvicorn app.main:app --reload
```
Visit `http://localhost:8000` to start your business analysis.

---

## 📝 Configuration

-   **LLM Config**: Modify `app/api_llm_service.py` to change model types (default: `qwen/qwen-2-72b-instruct`).
-   **Embedding Config**: Update `app/rag.py` to use different HuggingFace models.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 🌍 Short Arabic Summary

هذا المشروع يوفّر أداة RAG متكاملة لقراءة نصوص من قاعدة بيانات SQL، فهرستها في Chroma باستخدام تمثيلات متجهية، ثم استخدام هذه الوثائق كملخص سياقي مع نموذج لغوي لإنتاج خطط أو نصائح تجارية دقيقة.
