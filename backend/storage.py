# Upload storage limits and usage tracking per session workspace.

import os
from pathlib import Path

from backend.users import get_user_uploads_dir

_DEFAULT_LIMIT_MB = 25


def upload_limit_bytes() -> int:
    raw = os.getenv("UPLOAD_STORAGE_LIMIT_MB", str(_DEFAULT_LIMIT_MB)).strip()
    try:
        mb = int(raw)
    except ValueError as exc:
        raise ValueError(
            f"UPLOAD_STORAGE_LIMIT_MB must be an integer, got {raw!r}."
        ) from exc
    if mb <= 0:
        raise ValueError("UPLOAD_STORAGE_LIMIT_MB must be greater than 0.")
    return mb * 1024 * 1024


def dir_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def get_storage_usage(user_id: str) -> tuple[int, int]:
    used = dir_size_bytes(get_user_uploads_dir(user_id))
    limit = upload_limit_bytes()
    return used, limit


def check_upload_capacity(
    user_id: str,
    incoming_files: list[tuple[str, int]],
) -> tuple[bool, str | None]:
    """Check capacity. Each item is (filename, byte_size). Replaces count against same name."""
    used, limit = get_storage_usage(user_id)
    uploads_dir = get_user_uploads_dir(user_id)
    delta = 0
    for name, size in incoming_files:
        existing = uploads_dir / name
        if existing.exists():
            delta += size - existing.stat().st_size
        else:
            delta += size
    if delta <= 0:
        return True, None
    if used + delta > limit:
        remaining = max(0, limit - used)
        return False, (
            f"Storage limit exceeded. "
            f"Used {format_bytes(used)} of {format_bytes(limit)}. "
            f"These files need {format_bytes(delta)} more; "
            f"only {format_bytes(remaining)} remaining."
        )
    return True, None
