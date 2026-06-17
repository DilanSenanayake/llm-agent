# Per-session workspace paths, TTL, and automatic cleanup.

import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path

from backend.paths import PROJECT_ROOT

USERS_DIR = PROJECT_ROOT / "users"
_USER_ID_PATTERN = re.compile(r"^[a-z0-9]{8,64}$")
_DEFAULT_IDLE_MINUTES = 60


def _session_idle_seconds() -> int:
    raw = os.getenv("SESSION_IDLE_MINUTES", str(_DEFAULT_IDLE_MINUTES)).strip()
    try:
        minutes = int(raw)
    except ValueError as exc:
        raise ValueError(
            f"SESSION_IDLE_MINUTES must be an integer, got {raw!r}."
        ) from exc
    if minutes <= 0:
        raise ValueError("SESSION_IDLE_MINUTES must be greater than 0.")
    return minutes * 60


def generate_user_id() -> str:
    return uuid.uuid4().hex


def _validate_user_id(user_id: str) -> str:
    if not user_id or not _USER_ID_PATTERN.match(user_id):
        raise ValueError(f"Invalid internal user id: {user_id!r}")
    return user_id


def get_user_root(user_id: str) -> Path:
    return USERS_DIR / _validate_user_id(user_id)


def get_user_uploads_dir(user_id: str) -> Path:
    return get_user_root(user_id) / "uploads"


def get_user_index_dir(user_id: str) -> Path:
    return get_user_root(user_id) / "vector_db" / "faiss_index"


def _session_meta_path(user_id: str) -> Path:
    return get_user_root(user_id) / ".session.json"


def ensure_user_dirs(user_id: str) -> tuple[Path, Path]:
    uploads_dir = get_user_uploads_dir(user_id)
    index_dir = get_user_index_dir(user_id)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    index_dir.parent.mkdir(parents=True, exist_ok=True)
    return uploads_dir, index_dir


def create_session(user_id: str) -> None:
    now = time.time()
    meta = {"created_at": now, "last_activity_at": now}
    _session_meta_path(user_id).write_text(json.dumps(meta), encoding="utf-8")


def touch_session(user_id: str) -> None:
    path = _session_meta_path(user_id)
    now = time.time()
    if path.exists():
        meta = json.loads(path.read_text(encoding="utf-8"))
        meta["last_activity_at"] = now
    else:
        meta = {"created_at": now, "last_activity_at": now}
    path.write_text(json.dumps(meta), encoding="utf-8")


def session_idle_seconds_remaining(user_id: str) -> float:
    path = _session_meta_path(user_id)
    if not path.exists():
        return 0.0
    meta = json.loads(path.read_text(encoding="utf-8"))
    elapsed = time.time() - float(meta["last_activity_at"])
    return max(0.0, _session_idle_seconds() - elapsed)


def is_session_valid(user_id: str) -> bool:
    return session_idle_seconds_remaining(user_id) > 0


def delete_user_workspace(user_id: str) -> None:
    root = get_user_root(user_id)
    if root.exists():
        shutil.rmtree(root)


def cleanup_expired_sessions() -> None:
    if not USERS_DIR.exists():
        return
    for path in USERS_DIR.iterdir():
        if not path.is_dir() or not _USER_ID_PATTERN.match(path.name):
            continue
        if not is_session_valid(path.name):
            delete_user_workspace(path.name)
