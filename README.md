# Agentic Knowledge Workspace

Local-first MVP for **document upload → semantic indexing → RAG-powered summaries and reports** using **Streamlit**, **LangChain**, **FAISS**, **sentence-transformers** (`all-MiniLM-L6-v2`), and the **Gemini API**.

## Overview

Users upload **PDF** or **DOCX** files. The app extracts and cleans text, splits it into **500-word chunks with 50-word overlap**, embeds chunks, and stores them in a **local FAISS** index under `vector_db/`. When you click **Generate Summary** or **Generate Report**, a lightweight **agent** classifies intent, **retrieves** relevant chunks, and **Gemini** produces **markdown** grounded in that context.

## Architecture

```text
app.py (Streamlit)
    │
    ├── backend/document_loader.py   # PyPDF + python-docx, text cleanup
    ├── backend/chunker.py           # Word-based chunks (500 / 50 overlap)
    ├── backend/embeddings.py        # sentence-transformers MiniLM → LangChain Embeddings
    ├── backend/vector_store.py      # FAISS build / merge / save / load
    ├── backend/retriever.py         # similarity search + context formatting
    ├── backend/generator.py         # Gemini prompts (summary vs report)
    └── backend/agent.py             # intent → retrieve → generate
```

- **Uploads** land in `uploads/` (no auth, single workspace on your machine).
- **Vector index** is persisted under `vector_db/faiss_index/` (local files only).

## How RAG works here

1. Documents are chunked and turned into embeddings with **all-MiniLM-L6-v2**.
2. Embeddings are stored in **FAISS** for fast similarity search.
3. Your instruction (and/or explicit Summary/Report button) drives a **query embedding**.
4. The **top similar chunks** are concatenated into a bounded **context block**.
5. **Gemini** is instructed to **only** use that context, reducing unsupported extrapolation.

## How the agent works

Flow: **User instruction → intent → retrieval → generation → markdown output**.

- **Intent**: keyword-style (`summary` vs `report`); the Streamlit buttons **force** the mode so you do not have to type “summary” or “report”.
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

Copy `.env.example` to `.env` and set your Gemini key:

```powershell
copy .env.example .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes* | Google AI Studio / Gemini API key |
| `GOOGLE_API_KEY` | Yes* | Alternative name also supported by the code |
| `GEMINI_MODEL` | No | Defaults to `gemini-3-flash-preview` (auto-fallback if unavailable) |
| `SENTENCE_TRANSFORMERS_HOME` | No | Optional cache directory for embedding models |

\*Provide at least one of `GEMINI_API_KEY` or `GOOGLE_API_KEY`.

### 3. Run the app

```powershell
streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

## Expected user flow

1. Upload one or more **PDF** / **DOCX** files.
2. Click **Process uploaded documents** (embeddings + FAISS update).
3. Enter an instruction (optional but improves retrieval focus).
4. Click **Generate Summary** or **Generate Report**.
5. Read the markdown result; optionally **download as TXT**.

## Screenshots

Add your own screenshots under `docs/screenshots/` and reference them here, for example:

![Upload and process](docs/screenshots/upload-process.png)

![Summary output](docs/screenshots/summary-output.png)

![Report output](docs/screenshots/report-output.png)

*(Placeholder paths — create the folder and images when documenting the project.)*

## Limitations (MVP scope)

No authentication, multi-user features, payments, external link ingestion, collaboration UI, dashboards, or server-side databases — **local files only**.

## License

Use and modify for your own projects; add a license file if you redistribute.
