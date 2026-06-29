# DocuChat

Local-first MVP for **document upload → semantic indexing → RAG-powered Q&A** using **Streamlit**, **LangChain** (documents + FAISS), **sentence-transformers** (`all-MiniLM-L6-v2`), and the **Google Gen AI SDK** (Gemini).

## Overview

Users upload **PDF** or **DOCX** files in the sidebar. The app extracts and chunks text, embeds passages, and stores them in a **per-session FAISS** index. Each chat message uses your **instruction** to retrieve relevant passages and **Gemini** streams a **markdown** reply with source citations.

## Architecture

```text
app.py (Streamlit)
    │
    ├── backend/paths.py             # PROJECT_ROOT, uploads/, vector_db/ paths
    ├── backend/document_loader.py   # PyPDF + python-docx, text cleanup
    ├── backend/chunker.py           # Word-based chunks (500 / 50 overlap)
    ├── backend/embeddings.py        # sentence-transformers MiniLM → LangChain Embeddings
    ├── backend/vector_store.py      # FAISS build / merge / save / load
    ├── backend/retriever.py         # similarity search + context formatting
    ├── backend/generator.py         # Gemini prompts (per format, google.genai)
    └── backend/agent.py             # instruction → retrieve → generate
```

- **Uploads** land in `uploads/` (no auth, single workspace on your machine).
- **Vector index** is persisted under `vector_db/faiss_index/` (local files only).
- See `docs/ARCHITECTURE.txt` for a full system design reference.

## How RAG works here

1. Documents are chunked and turned into embeddings with **all-MiniLM-L6-v2**.
2. Embeddings are stored in **FAISS** for fast similarity search.
3. Your instruction drives a **query embedding** for similarity search.
4. The **top similar chunks** are concatenated into a bounded **context block** (max ~12k characters).
5. **Gemini** is instructed to **only** use that context, reducing unsupported extrapolation.

## How generation works

Flow: **User instruction → retrieval → generation → markdown output**.

- **Response formats**: Answer, Brief summary, Extract, Compare (selected in the UI).
- **Instruction is required** — it is used both to retrieve relevant chunks and to steer the answer.
- **No autonomous tool loops** — one retrieval pass and one LLM call per generation.

## Setup

### 1. Install dependencies (global, no venv)

From the project folder, install into your system/user Python (no virtual environment):

```powershell
cd d:\Github\llm-agent
python -m pip install -r requirements.txt
```

On Windows, if `python` is not on your PATH, try `py -m pip install -r requirements.txt` instead.

**Note:** Global installs affect every Python project on that interpreter. If you later hit version conflicts, use a venv (optional section below).

<details>
<summary>Optional: install with a virtual environment</summary>

```powershell
cd d:\Github\llm-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

</details>

### 2. Environment variables

Create a `.env` file in the project root with your Gemini API key:

```powershell
# .env
GEMINI_API_KEY=your_key_here
```

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes* | Google AI Studio / Gemini API key |
| `GOOGLE_API_KEY` | Yes* | Alternative name also supported by the code |
| `GEMINI_MODEL` | No | Defaults to `gemini-3-flash-preview` (auto-fallback if unavailable) |
| `SENTENCE_TRANSFORMERS_HOME` | No | Optional cache directory for embedding models |

\*Provide at least one of `GEMINI_API_KEY` or `GOOGLE_API_KEY`.

For **Streamlit Cloud**, set the same values in `.streamlit/secrets.toml` instead of committing `.env`.

### 3. Run the app

```powershell
streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

The first run may be slow while **all-MiniLM-L6-v2** downloads; later runs use the local cache.

## Expected user flow

1. Open **DocuChat** (`streamlit run app.py`).
2. Upload **PDF** or **DOCX** files in the sidebar (indexed automatically).
3. Pick a **format** in the chat bar: Answer, Brief summary, Extract, Compare — or **Auto** to detect from your message.
4. Type a **focused question or instruction** (required) and send.
5. Read the streamed reply with **source citations**; continue the conversation for follow-ups.

**Formats:**

| Format | Use for |
|--------|---------|
| **Answer** | Direct answer to a specific question |
| **Brief summary** | Short overview of a topic you name |
| **Extract** | Lists, tables, or key facts only |
| **Compare** | Side-by-side — name both items in your message |
| **Auto** | Infers format from keywords (compare, summarize, list, etc.) |

**Sidebar:** document list, storage usage, default format, and **Clear workspace** in Settings.

## Screenshots

Add your own screenshots under `docs/screenshots/` and reference them here, for example:

![Upload and process](docs/screenshots/upload-process.png)

![Generated output](docs/screenshots/generated-output.png)

*(Placeholder paths — create the folder and images when documenting the project.)*

## Limitations (MVP scope)

No authentication, multi-user features, payments, external link ingestion, collaboration UI, dashboards, or server-side databases — **local files only**.

## License

Use and modify for your own projects; add a license file if you redistribute.
