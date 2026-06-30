(function () {
  'use strict';

  const cfg = window.DOCUCHAT || {};
  const app = document.body;
  const sidebar = document.getElementById('dc-sidebar');
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
  const settingsForm = document.querySelector('.dc-settings-form');

  function csrfToken() {
    const input = chatForm && chatForm.querySelector('[name=csrfmiddlewaretoken]');
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

  function updateFormatHint() {
    if (!formatHint || !settingsSelect || !cfg.formatDescriptions) return;
    formatHint.textContent = cfg.formatDescriptions[settingsSelect.value] || '';
  }

  if (settingsSelect) {
    updateFormatHint();
    settingsSelect.addEventListener('change', function () {
      updateFormatHint();
      if (settingsForm) settingsForm.submit();
    });
  }

  if (uploadForm) {
    const fileInput = uploadForm.querySelector('input[type=file]');
    if (fileInput) {
      fileInput.addEventListener('change', function () {
        if (!fileInput.files || !fileInput.files.length) return;
        if (indexPanel) {
          indexPanel.hidden = false;
          if (indexLabel) indexLabel.textContent = 'Uploading & indexing…';
        }
        uploadForm.submit();
      });
    }
  }

  function ensureMessagesContainer() {
    let home = document.getElementById('dc-home');
    if (home) home.remove();
    let container = document.getElementById('dc-messages');
    if (!container) {
      container = document.createElement('div');
      container.id = 'dc-messages';
      container.className = 'dc-messages';
      if (content) content.appendChild(container);
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
    const container = ensureMessagesContainer();
    const article = document.createElement('article');
    article.className = 'dc-message dc-message-user';
    article.innerHTML = '<div class="dc-message-body"><div class="dc-markdown"></div></div>';
    article.querySelector('.dc-markdown').textContent = text;
    container.appendChild(article);
    container.scrollTop = container.scrollHeight;
    return article;
  }

  function appendAssistantPlaceholder() {
    const container = ensureMessagesContainer();
    const article = document.createElement('article');
    article.className = 'dc-message dc-message-assistant dc-message-streaming';
    article.innerHTML =
      '<div class="dc-message-body"><div class="dc-stream-body">' +
      loadingHtml('Searching your documents') +
      '</div></div>';
    container.appendChild(article);
    container.scrollTop = container.scrollHeight;
    return article.querySelector('.dc-stream-body');
  }

  function setStreamingLabel(slot, label) {
    if (slot) slot.innerHTML = loadingHtml(label);
  }

  async function streamChat(prompt, format, options) {
    options = options || {};
    const sendBtn = chatForm && chatForm.querySelector('.dc-send-btn');
    if (sendBtn) sendBtn.disabled = true;

    if (!options.retry) {
      appendUserMessage(prompt);
    }

    const slot = appendAssistantPlaceholder();
    let accumulated = '';

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

          if (payload.error) {
            accumulated = payload.error;
            slot.innerHTML =
              '<div class="dc-alert dc-alert-error">' + escapeHtml(payload.error) + '</div>';
          }

          if (payload.text) {
            if (!accumulated) setStreamingLabel(slot, 'Thinking…');
            accumulated += payload.text;
            slot.innerHTML =
              '<div class="dc-markdown" style="white-space:pre-wrap">' +
              escapeHtml(accumulated) +
              '</div>';
          }

          if (payload.done) {
            const parent = slot.closest('.dc-message');
            if (parent) parent.classList.remove('dc-message-streaming');

            if (payload.failed) {
              parent.classList.add('dc-message-error');
              const errText = payload.error || accumulated.replace(/^⚠️\s*/, '');
              let html =
                '<div class="dc-alert dc-alert-error">' + escapeHtml(errText) + '</div>' +
                '<button type="button" class="dc-retry-btn" data-index="' +
                payload.retry_idx +
                '" data-prompt="' +
                escapeAttr(payload.retry_prompt || prompt) +
                '" data-format="' +
                escapeAttr(payload.retry_format || format) +
                '">Retry</button>';
              slot.innerHTML = html;
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
        }

        const container = document.getElementById('dc-messages');
        if (container) container.scrollTop = container.scrollHeight;
      }
    } catch (err) {
      slot.innerHTML =
        '<div class="dc-alert dc-alert-error">' + escapeHtml(err.message || String(err)) + '</div>';
    } finally {
      if (sendBtn) sendBtn.disabled = false;
      if (chatInput) chatInput.value = '';
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

  if (chatForm) {
    chatForm.addEventListener('submit', function (e) {
      e.preventDefault();
      const prompt = (chatInput && chatInput.value || '').trim();
      if (!prompt) {
        alert('Enter a question or instruction.');
        return;
      }
      const format = chatFormat ? chatFormat.value : 'auto';
      streamChat(prompt, format);
    });
  }

  document.querySelectorAll('.dc-chip-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      streamChat(btn.dataset.prompt, btn.dataset.format);
    });
  });

  // Persist session id in URL (like Streamlit ?sid=)
  if (cfg.sessionParam) {
    const url = new URL(window.location.href);
    if (url.searchParams.get('sid') !== cfg.sessionParam) {
      url.searchParams.set('sid', cfg.sessionParam);
      window.history.replaceState({}, '', url.toString());
    }
  }
})();
