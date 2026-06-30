# Workspace session, vector store cache, and shared app logic.

from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import HttpRequest

from backend.chats import append_message, get_messages, reset_chats, set_messages
from backend.documents import (
    indexed_file_names,
    list_uploaded_documents,
    process_uploaded_files,
    remove_uploaded_documents,
)
from backend.storage import format_bytes, get_storage_usage
from backend.users import (
    cleanup_expired_sessions,
    create_session,
    delete_user_workspace,
    ensure_user_dirs,
    generate_user_id,
    get_user_index_dir,
    get_user_uploads_dir,
    is_session_valid,
    restore_user_id,
    touch_session,
)
from backend.vector_store import clear_vector_store, load_vector_store

if TYPE_CHECKING:
    from langchain_community.vectorstores import FAISS

_store_cache: dict[str, FAISS | None] = {}


def _friendly_error(exc: BaseException) -> str:
    return str(exc).strip() or exc.__class__.__name__


def ensure_user_id(request: HttpRequest) -> str:
    cleanup_expired_sessions()

    user_id = request.session.get("user_id")
    if user_id and is_session_valid(user_id):
        touch_session(user_id)
        request.session["user_id"] = user_id
        return user_id

    if user_id:
        delete_user_workspace(user_id)

    restored = restore_user_id(request.GET.get("sid"))
    if restored:
        request.session["user_id"] = restored
        _store_cache.pop(restored, None)
        return restored

    user_id = generate_user_id()
    ensure_user_dirs(user_id)
    create_session(user_id)
    request.session["user_id"] = user_id
    _store_cache.pop(user_id, None)
    reset_chats(user_id)
    return user_id


def get_store(user_id: str):
    if user_id not in _store_cache:
        _store_cache[user_id] = load_vector_store(get_user_index_dir(user_id))
    return _store_cache[user_id]


def invalidate_store(user_id: str) -> None:
    _store_cache[user_id] = load_vector_store(get_user_index_dir(user_id))


def clear_workspace(user_id: str) -> None:
    clear_vector_store(get_user_index_dir(user_id))
    uploads_dir = get_user_uploads_dir(user_id)
    if uploads_dir.exists():
        for path in uploads_dir.iterdir():
            if path.is_file() and path.name != ".gitkeep":
                path.unlink()
    _store_cache[user_id] = None
    reset_chats(user_id)


def sidebar_context(user_id: str) -> dict:
    docs = list_uploaded_documents(user_id)
    used, limit = get_storage_usage(user_id)
    return {
        "documents": docs,
        "storage_used": format_bytes(used),
        "storage_limit": format_bytes(limit),
        "doc_count": len(docs),
        "indexed_names": indexed_file_names(user_id),
    }


def handle_upload(user_id: str, files) -> tuple[bool, str]:
    if not files:
        return False, "No files selected."
    names, chunk_count, err = process_uploaded_files(files, user_id)
    if err:
        return False, err
    invalidate_store(user_id)
    append_message(
        user_id,
        {
            "role": "assistant",
            "kind": "system",
            "content": (
                f"Indexed **{', '.join(names)}** ({chunk_count} passages)."
            ),
        },
    )
    return True, f"Indexed {len(names)} file(s) ({chunk_count} passages)."


def handle_remove_documents(user_id: str, filenames: set[str]) -> str | None:
    if not filenames:
        return None
    err = remove_uploaded_documents(user_id, filenames)
    if err:
        return err
    invalidate_store(user_id)
    return None


__all__ = [
    "_friendly_error",
    "append_message",
    "clear_workspace",
    "ensure_user_id",
    "get_messages",
    "get_store",
    "handle_remove_documents",
    "handle_upload",
    "invalidate_store",
    "set_messages",
    "sidebar_context",
    "touch_session",
]
