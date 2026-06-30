(function () {
  'use strict';

  const cfg = window.DOCUCHAT || {};
  const app = document.body;
  const backdrop = document.getElementById('dc-backdrop');
  const menuBtn = document.getElementById('dc-menu-btn');
  const closeBtn = document.getElementById('dc-sidebar-close');
  const chatForm = document.getElementById('dc-chat-form');
  const chatInput = document.getElementById('dc-chat-input');
  const chatFormat = document.getElementById('dc-chat-format');
  const content = document.getElementById('dc-content');
  const uploadForm = document.getElementById('dc-upload-form');
  const indexPanel = document.getElementById('dc-index-panel');
  const indexLabel = document.getElementById('dc-index-label');
  const settingsSelect = document.getElementById('settings_format');
  const formatHint = document.getElementById('dc-format-hint');
  const flash = document.getElementById('dc-flash');

  let hydrated = false;
  let streaming = false;

  const AVATAR_USER =
    '<div class="dc-avatar dc-avatar-user" aria-hidden="true">' +
    '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z"/></svg></div>';
  const AVATAR_BOT =
    '<div class="dc-avatar dc-avatar-bot" aria-hidden="true">' +
    '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l1.8 5.5L19 9.3l-5.2 1.8L12 16.5 10.2 11 5 9.3l5.2-1.8L12 2zM5 17l.9 2.7L8.6 21l-2.7-.9L3 21l.9-2.7L5 17zm14 0l.9 2.7 2.7.9-2.7.9-.9 2.7-.9-2.7-2.7-.9 2.7-.9.9-2.7z"/></svg></div>';
  const AVATAR_SYSTEM =
    '<div class="dc-avatar dc-avatar-system" aria-hidden="true">' +
    '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 2l5 5h-5V4zM8 13h8v2H8v-2zm0 4h5v2H8v-2z"/></svg></div>';

  function csrfToken() {
    const root = chatForm || uploadForm;
    const input = root && root.querySelector('[name=csrfmiddlewaretoken]');
    return input ? input.value : '';
  }

  function openSidebar() {
    app.classList.add('dc-sidebar-open');
    if (backdrop) backdrop.hidden = false;
  }

  function closeSidebar() {
    app.classList.remove('dc-sidebar-open');
    if (backdrop) backdrop.hidden = true;
  }

  if (menuBtn) menuBtn.addEventListener('click', openSidebar);
  if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
  if (backdrop) backdrop.addEventListener('click', closeSidebar);

  function scrollContent() {
    if (content) content.scrollTop = content.scrollHeight;
  }

  function autoResizeTextarea() {
    if (!chatInput) return;
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 192) + 'px';
  }

  function enterChatMode() {
    document.body.classList.add('dc-has-chat');
    const home = document.getElementById('dc-home');
    if (home) home.remove();
    const suggestions = document.getElementById('dc-suggestions');
    if (suggestions) suggestions.remove();
  }

  function avatarFor(role, kind) {
    if (role === 'user') return AVATAR_USER;
    if (kind === 'system') return AVATAR_SYSTEM;
    return AVATAR_BOT;
  }

  function wrapMessage(role, kind, inner, extraClass, dataIndex) {
    const classes = ['dc-message', 'dc-message-' + role];
    if (kind === 'system') classes.push('dc-message-system');
    if (extraClass) classes.push(extraClass);
    let attrs = '';
    if (dataIndex !== undefined && dataIndex !== null) {
      attrs = ' data-index="' + dataIndex + '"';
    }
    return (
      '<article class="' + classes.join(' ') + '"' + attrs + '>' +
      '<div class="dc-message-row">' +
      avatarFor(role, kind) +
      '<div class="dc-message-body">' + inner + '</div>' +
      '</div></article>'
    );
  }

  function updateFormatHint() {
    if (!formatHint || !settingsSelect || !cfg.formatDescriptions) return;
    formatHint.textContent = cfg.formatDescriptions[settingsSelect.value] || '';
  }

  function syncChatFormatFromSettings(label) {
    if (!chatFormat) return;
    for (let i = 0; i < chatFormat.options.length; i++) {
      if (chatFormat.options[i].text === label) {
        chatFormat.selectedIndex = i;
        break;
      }
    }
  }

  async function saveSettings(label) {
    if (!cfg.settingsUrl) return;
    const body = new FormData();
    body.append('csrfmiddlewaretoken', csrfToken());
    body.append('settings_format', label);
    try {
      await fetch(cfg.settingsUrl, {
        method: 'POST',
        body: body,
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      syncChatFormatFromSettings(label);
    } catch (e) {
      /* non-fatal */
    }
  }

  if (settingsSelect) {
    updateFormatHint();
    settingsSelect.addEventListener('change', function () {
      updateFormatHint();
      saveSettings(settingsSelect.value);
    });
  }

  if (uploadForm) {
    const fileInput = uploadForm.querySelector('input[type=file]');

    function setUploadBusy(busy, label) {
      uploadForm.classList.toggle('is-busy', busy);
      if (indexPanel) {
        indexPanel.hidden = !busy;
        indexPanel.setAttribute('aria-busy', busy ? 'true' : 'false');
      }
      if (indexLabel) {
        indexLabel.innerHTML = '<strong>' + escapeHtml(label || 'Uploading & indexing…') + '</strong>';
      }
      if (fileInput) fileInput.disabled = busy;
    }

    async function uploadFiles(files) {
      if (!files || !files.length) return;

      setUploadBusy(true, 'Uploading & indexing…');

      const body = new FormData();
      body.append('csrfmiddlewaretoken', csrfToken());
      for (let i = 0; i < files.length; i++) {
        body.append('documents', files[i]);
      }

      try {
        const response = await fetch(cfg.uploadUrl, {
          method: 'POST',
          body: body,
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
        });
        const data = await response.json().catch(function () { return {}; });

        if (!response.ok || !data.ok) {
          throw new Error(data.error || 'Upload failed');
        }

        setUploadBusy(true, 'Done — refreshing…');
        window.location.reload();
      } catch (err) {
        setUploadBusy(false);
        if (fileInput) fileInput.value = '';
        showToast(err.message || 'Upload failed');
      }
    }

    if (fileInput) {
      fileInput.addEventListener('change', function () {
        const files = fileInput.files;
        if (!files || !files.length) return;
        uploadFiles(files);
      });
    }
  }

  if (flash) {
    setTimeout(function () {
      flash.style.opacity = '0';
      setTimeout(function () { flash.remove(); }, 300);
    }, 4500);
  }

  function messageHtml(msg) {
    const role = msg.role || 'assistant';
    const kind = msg.kind || 'chat';
    const extraClass = msg.error ? 'dc-message-error' : '';

    let inner = '';
    if (msg.format_label && !msg.error) {
      inner += '<p class="dc-message-format">' + escapeHtml(msg.format_label) + '</p>';
    }
    if (msg.error) {
      const errText = (msg.content || '').replace(/^⚠️\s*/, '');
      inner +=
        '<div class="dc-alert dc-alert-error">' + escapeHtml(errText) + '</div>' +
        '<button type="button" class="dc-retry-btn" data-index="' + msg.index +
        '" data-prompt="' + escapeAttr(msg.retry_prompt || '') +
        '" data-format="' + escapeAttr(msg.retry_format || 'auto') +
        '">Retry</button>';
    } else {
      inner += '<div class="dc-markdown">' + (msg.html || escapeHtml(msg.content || '')) + '</div>';
    }

    return wrapMessage(role, kind, inner, extraClass, msg.index);
  }

  function ensureMessagesContainer() {
    const home = document.getElementById('dc-home');
    if (home) home.remove();

    let container = document.getElementById('dc-messages');
    if (!container) {
      container = document.createElement('div');
      container.id = 'dc-messages';
      container.className = 'dc-messages';
      if (content) content.appendChild(container);
    }

    if (!hydrated && cfg.initialMessages && cfg.initialMessages.length) {
      container.innerHTML = cfg.initialMessages.map(messageHtml).join('');
      bindRetryButtons(container);
      hydrated = true;
      scrollContent();
    }

    return container;
  }

  function loadingHtml(label) {
    return (
      '<div class="dc-loader">' +
      '<span class="dc-loader-dots"><span></span><span></span><span></span></span>' +
      '<span>' + label + '</span></div>'
    );
  }

  function appendUserMessage(text) {
    enterChatMode();
    const container = ensureMessagesContainer();
    const html = wrapMessage(
      'user',
      'chat',
      '<div class="dc-markdown">' + escapeHtml(text) + '</div>'
    );
    container.insertAdjacentHTML('beforeend', html);
    scrollContent();
  }

  function appendAssistantPlaceholder() {
    const container = ensureMessagesContainer();
    const html = wrapMessage(
      'assistant',
      'chat',
      '<div class="dc-stream-body">' + loadingHtml('Searching your documents') + '</div>',
      'dc-message-streaming'
    );
    container.insertAdjacentHTML('beforeend', html);
    scrollContent();
    const articles = container.querySelectorAll('.dc-message-streaming');
    return articles[articles.length - 1].querySelector('.dc-stream-body');
  }

  function setStreaming(active) {
    streaming = active;
    const sendBtn = chatForm && chatForm.querySelector('.dc-send-btn');
    if (sendBtn) sendBtn.disabled = active;
    if (chatInput) chatInput.disabled = active;
    if (chatFormat) chatFormat.disabled = active;
    document.querySelectorAll('.dc-chip-btn').forEach(function (btn) {
      btn.disabled = active;
    });
  }

  function showToast(text) {
    let el = document.getElementById('dc-toast');
    if (!el) {
      el = document.createElement('div');
      el.id = 'dc-toast';
      el.className = 'dc-toast';
      document.body.appendChild(el);
    }
    el.textContent = text;
    el.classList.add('dc-toast-visible');
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(function () {
      el.classList.remove('dc-toast-visible');
    }, 2800);
  }

  async function streamChat(prompt, format, options) {
    options = options || {};
    if (streaming) return;

    setStreaming(true);

    if (!options.retry) {
      appendUserMessage(prompt);
    }

    const slot = appendAssistantPlaceholder();
    let accumulated = '';
    let sawText = false;

    const body = new FormData();
    body.append('csrfmiddlewaretoken', csrfToken());
    body.append('prompt', prompt);
    body.append('format', format || 'auto');
    if (options.retry) {
      body.append('retry', '1');
      body.append('retry_idx', String(options.retryIdx));
    }

    try {
      const response = await fetch(cfg.streamUrl, {
        method: 'POST',
        body: body,
        headers: { Accept: 'text/event-stream' },
      });

      if (!response.ok) {
        const data = await response.json().catch(function () { return {}; });
        throw new Error(data.error || 'Request failed');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const result = await reader.read();
        if (result.done) break;
        buffer += decoder.decode(result.value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (let i = 0; i < parts.length; i++) {
          const line = parts[i].trim();
          if (!line.startsWith('data: ')) continue;
          let payload;
          try {
            payload = JSON.parse(line.slice(6));
          } catch (e) {
            continue;
          }

          if (payload.error && !payload.done) {
            accumulated = payload.error;
            slot.innerHTML =
              '<div class="dc-alert dc-alert-error">' + escapeHtml(payload.error) + '</div>';
          }

          if (payload.text) {
            if (!sawText) {
              sawText = true;
              slot.innerHTML = '<div class="dc-markdown dc-stream-text"></div>';
            }
            accumulated += payload.text;
            const streamEl = slot.querySelector('.dc-stream-text');
            if (streamEl) streamEl.textContent = accumulated;
          }

          if (payload.done) {
            const parent = slot.closest('.dc-message');
            if (parent) parent.classList.remove('dc-message-streaming');

            if (payload.failed) {
              parent.classList.add('dc-message-error');
              const errText = payload.error || accumulated.replace(/^⚠️\s*/, '');
              slot.innerHTML =
                '<div class="dc-alert dc-alert-error">' + escapeHtml(errText) + '</div>' +
                '<button type="button" class="dc-retry-btn" data-index="' +
                payload.retry_idx +
                '" data-prompt="' +
                escapeAttr(payload.retry_prompt || prompt) +
                '" data-format="' +
                escapeAttr(payload.retry_format || format) +
                '">Retry</button>';
              bindRetryButtons(parent);
            } else {
              let html = '';
              if (payload.format_label) {
                html += '<p class="dc-message-format">' + escapeHtml(payload.format_label) + '</p>';
              }
              html += '<div class="dc-markdown">' + (payload.html || escapeHtml(accumulated)) + '</div>';
              slot.innerHTML = html;
            }
          }

          scrollContent();
        }
      }
    } catch (err) {
      slot.innerHTML =
        '<div class="dc-alert dc-alert-error">' + escapeHtml(err.message || String(err)) + '</div>';
    } finally {
      setStreaming(false);
      if (chatInput) {
        chatInput.value = '';
        autoResizeTextarea();
        chatInput.focus();
      }
      scrollContent();
    }
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  function escapeAttr(text) {
    return String(text || '')
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/</g, '&lt;');
  }

  function bindRetryButtons(root) {
    const scope = root || document;
    scope.querySelectorAll('.dc-retry-btn').forEach(function (btn) {
      if (btn.dataset.bound) return;
      btn.dataset.bound = '1';
      btn.addEventListener('click', function () {
        const article = btn.closest('.dc-message');
        if (article) article.remove();
        streamChat(btn.dataset.prompt, btn.dataset.format, {
          retry: true,
          retryIdx: btn.dataset.index,
        });
      });
    });
  }

  bindRetryButtons(document);

  if (document.getElementById('dc-messages')) {
    hydrated = true;
    scrollContent();
  }

  if (chatForm) {
    if (chatInput) {
      chatInput.addEventListener('input', autoResizeTextarea);
      chatInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          chatForm.requestSubmit();
        }
      });
    }

    chatForm.addEventListener('submit', function (e) {
      e.preventDefault();
      const prompt = (chatInput && chatInput.value || '').trim();
      if (!prompt) {
        showToast('Enter a question or instruction.');
        return;
      }
      const format = chatFormat ? chatFormat.value : 'auto';
      streamChat(prompt, format);
    });
  }

  document.querySelectorAll('.dc-chip-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      enterChatMode();
      if (chatFormat && btn.dataset.format) {
        for (let i = 0; i < chatFormat.options.length; i++) {
          if (chatFormat.options[i].value === btn.dataset.format) {
            chatFormat.selectedIndex = i;
            break;
          }
        }
      }
      streamChat(btn.dataset.prompt, btn.dataset.format);
    });
  });

  if (cfg.sessionParam) {
    const url = new URL(window.location.href);
    if (url.searchParams.get('sid') !== cfg.sessionParam) {
      url.searchParams.set('sid', cfg.sessionParam);
      window.history.replaceState({}, '', url.toString());
    }
  }
})();
