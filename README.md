# DocuChat

Local-first MVP for **document upload → semantic indexing → RAG-powered Q&A** using **Django**, **LangChain** (documents + FAISS), **sentence-transformers** (`all-MiniLM-L6-v2`), and the **Google Gen AI SDK** (Gemini).

## Overview

Users upload **PDF** or **DOCX** files in the sidebar. The app extracts and chunks text, embeds passages, and stores them in a **per-session FAISS** index. Each chat message uses your **instruction** to retrieve relevant passages and **Gemini** streams a **markdown** reply with source citations.

## Architecture

```text
manage.py (Django)
    │
    ├── chat/                        # Views, templates, static UI
    ├── backend/paths.py             # PROJECT_ROOT, uploads/, vector_db/ paths
    ├── backend/document_loader.py   # PyPDF + python-docx, text cleanup
    ├── backend/chunker.py           # Word-based chunks (500 / 50 overlap)
    ├── backend/embeddings.py        # sentence-transformers MiniLM → LangChain Embeddings
    ├── backend/vector_store.py      # FAISS build / merge / save / load
    ├── backend/retriever.py         # similarity search + context formatting
    ├── backend/generator.py         # Gemini prompts (per format, google.genai)
    └── backend/agent.py             # instruction → retrieve → generate
```

- **Uploads** land in `users/<session-id>/uploads/` (anonymous per-browser session).
- **Vector index** is persisted under `users/<session-id>/vector_db/faiss_index/`.
- Sessions expire after idle timeout (`SESSION_IDLE_MINUTES`, default 60).

## Setup

### 1. Install dependencies

```powershell
cd d:\Github\llm-agent
python -m pip install -r requirements.txt
```

### 2. Environment variables

Create a `.env` file in the project root:

```powershell
GEMINI_API_KEY=your_key_here
```

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes* | Google AI Studio / Gemini API key |
| `GOOGLE_API_KEY` | Yes* | Alternative name also supported |
| `GEMINI_MODEL` | No | Defaults to `gemini-3-flash-preview` |
| `DJANGO_SECRET_KEY` | No | Production secret key |
| `DJANGO_DEBUG` | No | `true` (default) or `false` |
| `SESSION_IDLE_MINUTES` | No | Workspace TTL (default 60) |
| `UPLOAD_STORAGE_LIMIT_MB` | No | Per-session upload cap (default 25) |

\*Provide at least one of `GEMINI_API_KEY` or `GOOGLE_API_KEY`.

### 3. Run migrations and start the server

```powershell
python manage.py migrate
python manage.py runserver
```

Open **http://127.0.0.1:8000/** in your browser.

The first run may be slow while **all-MiniLM-L6-v2** downloads; later runs use the local cache.

## Expected user flow

1. Open **DocuChat** (`python manage.py runserver`).
2. Upload **PDF** or **DOCX** files in the sidebar (indexed automatically).
3. Pick a **format** in the chat bar: Answer, Brief summary, Extract, Compare — or **Auto**.
4. Type a **focused question or instruction** and send.
5. Read the streamed reply with **source citations**; continue the conversation for follow-ups.

**Sidebar:** document list (click to remove), storage usage, default format in Settings, and **Clear workspace**.

## License

Use and modify for your own projects; add a license file if you redistribute.
