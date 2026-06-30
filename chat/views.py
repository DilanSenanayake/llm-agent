import json
from typing import Literal

import markdown
from django.contrib import messages
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from backend.agent import stream_agent
from backend.generator import ResponseFormat
from chat.constants import (
    FORMAT_DESCRIPTIONS,
    FORMAT_LABELS,
    FORMAT_OPTIONS,
    SESSION_QP,
    SUGGESTED_PROMPTS,
)
from chat.services import (
    _friendly_error,
    append_message,
    clear_workspace,
    get_messages,
    get_store,
    handle_remove_documents,
    handle_upload,
    set_messages,
    sidebar_context,
    touch_session,
)


def _render_markdown(text: str) -> str:
    return markdown.markdown(text or "", extensions=["tables", "fenced_code", "nl2br"])


def _message_display(messages: list[dict]) -> list[dict]:
    out: list[dict] = []
    for idx, message in enumerate(messages):
        if message.get("kind") == "system" and not message.get("content", "").startswith(
            "Indexed"
        ):
            continue
        item = dict(message)
        item["index"] = idx
        item["format_label"] = FORMAT_LABELS.get(message.get("format", ""), "")
        item["role"] = message.get("role", "assistant")
        item["kind"] = message.get("kind", "chat")
        if message.get("error"):
            item["error"] = True
            item["retry_prompt"] = message.get("retry_prompt", "")
            item["retry_format"] = message.get("retry_format", "auto")
        if not message.get("error"):
            item["html"] = _render_markdown(message.get("content", ""))
        out.append(item)
    return out


def _base_context(request, *, default_format: str = "Auto") -> dict:
    settings_format = request.session.get("settings_format", default_format)
    if settings_format not in FORMAT_OPTIONS:
        settings_format = "Auto"
    display_messages = _message_display(get_messages(request.user_id))
    msgs = get_messages(request.user_id)
    has_chat = any(
        m.get("kind") == "chat" and m.get("role") == "user" for m in msgs
    )
    return {
        "format_options": FORMAT_OPTIONS,
        "format_labels": FORMAT_LABELS,
        "format_descriptions": FORMAT_DESCRIPTIONS,
        "format_descriptions_json": json.dumps(FORMAT_DESCRIPTIONS),
        "format_labels_json": json.dumps(FORMAT_LABELS),
        "settings_format": settings_format,
        "session_id": request.user_id,
        SESSION_QP: request.user_id,
        "display_messages_json": json.dumps(display_messages),
        "has_chat": has_chat,
        **sidebar_context(request.user_id),
    }


def home(request):
    ctx = _base_context(request)
    ctx["messages"] = _message_display(get_messages(request.user_id))
    ctx["suggested_prompts"] = SUGGESTED_PROMPTS
    ctx["django_messages"] = list(messages.get_messages(request))
    return render(request, "chat/home.html", ctx)


def _redirect_home(request):
    sid = request.user_id
    return redirect(f"/?{SESSION_QP}={sid}")


@require_POST
def upload_documents(request):
    files = request.FILES.getlist("documents")
    ok, msg = handle_upload(request.user_id, files)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if ok:
        messages.success(request, msg)
        if is_ajax:
            return JsonResponse({"ok": True, "message": msg})
    else:
        messages.error(request, msg)
        if is_ajax:
            return JsonResponse({"ok": False, "error": msg}, status=400)
    return _redirect_home(request)


@require_POST
def remove_document(request):
    name = (request.POST.get("name") or "").strip()
    if name:
        err = handle_remove_documents(request.user_id, {name})
        if err:
            messages.error(request, err)
        else:
            messages.success(request, f"Removed {name}.")
    return _redirect_home(request)


@require_POST
def clear_workspace_view(request):
    clear_workspace(request.user_id)
    messages.success(request, "Workspace cleared.")
    return _redirect_home(request)


@require_POST
def update_settings(request):
    fmt = request.POST.get("settings_format", "Auto")
    if fmt in FORMAT_OPTIONS:
        request.session["settings_format"] = fmt
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "format": fmt})
    return _redirect_home(request)


@require_POST
def chat_stream(request):
    user_id = request.user_id
    prompt = (request.POST.get("prompt") or "").strip()
    response_format: ResponseFormat | Literal["auto"] = request.POST.get("format", "auto")
    if response_format not in (*FORMAT_OPTIONS.values(),):
        response_format = "auto"

    retry = request.POST.get("retry") == "1"
    retry_idx_raw = request.POST.get("retry_idx")

    if not prompt:
        return JsonResponse({"error": "Enter a question or instruction."}, status=400)

    prior: list[dict]
    if retry and retry_idx_raw is not None:
        try:
            retry_idx = int(retry_idx_raw)
        except ValueError:
            return JsonResponse({"error": "Invalid retry index."}, status=400)
        truncated = get_messages(user_id)[:retry_idx]
        set_messages(user_id, truncated)
        prior = list(truncated)
        if prior and prior[-1].get("role") == "user":
            prior = prior[:-1]
    else:
        prior = list(get_messages(user_id))
        append_message(
            user_id,
            {"role": "user", "content": prompt, "kind": "chat"},
        )

    def event_stream():
        store = get_store(user_id)
        if store is None:
            reply = "Upload at least one PDF or DOCX to get started."
            append_message(
                user_id,
                {"role": "assistant", "content": reply, "kind": "chat"},
            )
            yield f"data: {json.dumps({'text': reply, 'done': True, 'html': _render_markdown(reply)})}\n\n"
            return

        fmt: ResponseFormat | None = None
        failed = False
        reply = ""
        try:
            stream, fmt, _docs = stream_agent(
                store,
                user_instruction=prompt,
                response_format=response_format,
                chat_messages=prior,
            )
            parts: list[str] = []
            for chunk in stream:
                parts.append(chunk)
                yield f"data: {json.dumps({'text': chunk})}\n\n"
            reply = "".join(parts).strip()
            if not reply:
                reply = "No response was generated. Try again."
                failed = True
            elif reply.startswith("⚠️"):
                failed = True
            touch_session(user_id)
        except (ValueError, RuntimeError) as exc:
            failed = True
            reply = f"⚠️ {_friendly_error(exc)}"
            fmt = None
            yield f"data: {json.dumps({'error': _friendly_error(exc)})}\n\n"
        except Exception as exc:
            failed = True
            reply = f"⚠️ Unexpected error: {_friendly_error(exc)}"
            fmt = None
            yield f"data: {json.dumps({'error': f'Unexpected error: {_friendly_error(exc)}'})}\n\n"

        msg: dict = {"role": "assistant", "content": reply, "kind": "chat"}
        if fmt and not failed:
            msg["format"] = fmt
        if failed:
            msg["error"] = True
            msg["retry_prompt"] = prompt
            msg["retry_format"] = response_format
        append_message(user_id, msg)

        payload: dict = {
            "done": True,
            "failed": failed,
            "html": _render_markdown(reply.lstrip("⚠️").strip() if failed else reply),
        }
        if fmt and not failed:
            payload["format"] = fmt
            payload["format_label"] = FORMAT_LABELS.get(fmt, fmt)
        if failed:
            payload["retry_idx"] = len(get_messages(user_id)) - 1
            payload["retry_prompt"] = prompt
            payload["retry_format"] = response_format
        yield f"data: {json.dumps(payload)}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
