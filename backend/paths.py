# Project paths (no heavy third-party imports).

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UPLOADS_DIR = PROJECT_ROOT / "uploads"
DEFAULT_INDEX_DIR = PROJECT_ROOT / "vector_db" / "faiss_index"
