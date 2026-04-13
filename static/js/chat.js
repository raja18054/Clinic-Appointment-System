/* ───────────────────────────────────────────────────────────────
   NexusChat – chat.js
   Real-time WebSocket client for the chat room view.
─────────────────────────────────────────────────────────────── */

(function () {
  'use strict';

  // ── DOM refs ──────────────────────────────────────────────────
  const messagesArea      = document.getElementById('messagesArea');
  const messagesContainer = document.getElementById('messagesContainer');
  const messageInput      = document.getElementById('messageInput');
  const sendBtn           = document.getElementById('sendBtn');
  const attachBtn         = document.getElementById('attachBtn');
  const fileInput         = document.getElementById('fileInput');
  const filePreview       = document.getElementById('filePreview');
  const filePreviewImg    = document.getElementById('filePreviewImg');
  const filePreviewName   = document.getElementById('filePreviewName');
  const cancelFileBtn     = document.getElementById('cancelFileBtn');
  const typingIndicator   = document.getElementById('typingIndicator');
  const typingName        = document.getElementById('typingName');
  const headerStatus      = document.getElementById('headerStatus');
  const headerStatusDot   = document.getElementById('headerStatusDot');

  let pendingFile = null;
  let typingTimeout = null;
  let isTyping = false;

  // ── WebSocket ─────────────────────────────────────────────────
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const chatWsUrl = `${protocol}://${window.location.host}/ws/chat/${ROOM_ID}/`;
  const presenceWsUrl = `${protocol}://${window.location.host}/ws/presence/`;

  let chatWs = null;
  let presenceWs = null;
  let reconnectDelay = 1000;

  function connectChatWs() {
    chatWs = new WebSocket(chatWsUrl);

    chatWs.onopen = () => {
      console.log('[NexusChat] Chat WS connected');
      reconnectDelay = 1000;
      // Mark messages as read
      chatWs.send(JSON.stringify({ type: 'read_receipt' }));
      clearUnreadBadge();
    };

    chatWs.onmessage = (event) => {
      const data = JSON.parse(event.data);
      switch (data.type) {
        case 'chat_message':     handleIncomingMessage(data); break;
        case 'typing_indicator': handleTypingIndicator(data); break;
        case 'presence_update':  handlePresenceUpdate(data);  break;
      }
    };

    chatWs.onclose = () => {
      console.warn('[NexusChat] Chat WS closed – reconnecting in', reconnectDelay, 'ms');
      setTimeout(connectChatWs, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 2, 16000);
    };

    chatWs.onerror = (err) => console.error('[NexusChat] Chat WS error', err);
  }

  function connectPresenceWs() {
    presenceWs = new WebSocket(presenceWsUrl);

    presenceWs.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'user_status') handlePresenceUpdate(data);
    };

    presenceWs.onclose = () => {
      setTimeout(connectPresenceWs, 3000);
    };
  }

  connectChatWs();
  connectPresenceWs();

  // ── Scroll helpers ────────────────────────────────────────────
  function scrollToBottom(smooth = false) {
    messagesArea.scrollTo({
      top: messagesArea.scrollHeight,
      behavior: smooth ? 'smooth' : 'instant',
    });
  }
  scrollToBottom(); // initial

  function isNearBottom() {
    return messagesArea.scrollHeight - messagesArea.scrollTop - messagesArea.clientHeight < 120;
  }

  // ── Avatar HTML ───────────────────────────────────────────────
  function avatarHtml(username, avatarUrl, size = 'xs') {
    if (avatarUrl) {
      return `<img src="${avatarUrl}" class="avatar avatar--${size}" alt="${username}"/>`;
    }
    const letter = (username || '?')[0].toUpperCase();
    return `<div class="avatar avatar--${size} avatar--placeholder">${letter}</div>`;
  }

  // ── Render message ────────────────────────────────────────────
  function renderMessage(data) {
    const isOwn = data.sender_id === CURRENT_USER_ID;
    const wrapper = document.createElement('div');
    wrapper.className = `message-wrapper${isOwn ? ' message-wrapper--own' : ''}`;
    wrapper.id = `msg-${data.message_id}`;

    let bubbleContent = '';

    if (data.message_type === 'image') {
      bubbleContent = `
        <a href="${data.file_url}" target="_blank">
          <img src="${data.file_url}" class="message-image" alt="Image"/>
        </a>`;
    } else if (data.message_type === 'file') {
      bubbleContent = `
        <a href="${data.file_url}" class="message-file" target="_blank" download>
          <i class="fa fa-file"></i>
          <span>${escapeHtml(data.file_name || data.content)}</span>
          <i class="fa fa-download"></i>
        </a>`;
    } else {
      bubbleContent = `<p class="message-text">${escapeHtml(data.content)}</p>`;
    }

    wrapper.innerHTML = `
      ${!isOwn ? `<div class="message-avatar">${avatarHtml(data.sender_username, data.sender_avatar)}</div>` : ''}
      <div class="message-content-area">
        <div class="message-bubble${isOwn ? ' message-bubble--own' : ''}">
          ${bubbleContent}
          <span class="message-time">${data.timestamp}</span>
        </div>
      </div>`;

    return wrapper;
  }

  function handleIncomingMessage(data) {
    const nearBottom = isNearBottom();

    // Remove typing indicator if it was the sender
    if (data.sender_id !== CURRENT_USER_ID) {
      hideTyping();
    }

    const el = renderMessage(data);
    messagesContainer.insertBefore(el, typingIndicator);

    if (nearBottom) scrollToBottom(true);

    // Update sidebar preview
    updateSidebarPreview(data);

    // Mark as read if it's not our own message
    if (data.sender_id !== CURRENT_USER_ID) {
      if (chatWs && chatWs.readyState === WebSocket.OPEN) {
        chatWs.send(JSON.stringify({ type: 'read_receipt' }));
      }
    }
  }

  // ── Typing indicator ──────────────────────────────────────────
  function handleTypingIndicator(data) {
    if (data.sender_id === CURRENT_USER_ID) return;

    if (data.is_typing) {
      typingName.textContent = data.sender_username;
      typingIndicator.style.display = 'block';
      scrollToBottom(true);
    } else {
      hideTyping();
    }
  }

  function hideTyping() {
    typingIndicator.style.display = 'none';
  }

  // ── Presence ──────────────────────────────────────────────────
  function handlePresenceUpdate(data) {
    if (!headerStatusDot) return;

    // Update header status dot for the other user in private chats
    if (data.is_online) {
      headerStatusDot.classList.remove('status-dot--offline');
      headerStatusDot.classList.add('status-dot--online');
      if (headerStatus) {
        headerStatus.innerHTML = '<span class="online-text">Online</span>';
      }
    } else {
      headerStatusDot.classList.remove('status-dot--online');
      headerStatusDot.classList.add('status-dot--offline');
      if (headerStatus) {
        headerStatus.textContent = 'Offline';
      }
    }
  }

  // ── Sidebar preview update ────────────────────────────────────
  function updateSidebarPreview(data) {
    const previewEl = document.getElementById(`room-preview-${ROOM_ID}`);
    const timeEl    = document.getElementById(`room-time-${ROOM_ID}`);

    if (previewEl) {
      let preview = '';
      if (data.message_type === 'image') preview = '📷 Photo';
      else if (data.message_type === 'file') preview = '📎 File';
      else preview = truncate(data.content, 35);
      previewEl.textContent = preview;
    }
    if (timeEl) timeEl.textContent = data.timestamp;
  }

  function clearUnreadBadge() {
    const badge = document.getElementById(`room-unread-${ROOM_ID}`);
    if (badge) badge.classList.add('hidden');
  }

  // ── Send message ──────────────────────────────────────────────
  function sendMessage() {
    if (pendingFile) {
      sendFile();
      return;
    }

    const content = messageInput.value.trim();
    if (!content) return;
    if (!chatWs || chatWs.readyState !== WebSocket.OPEN) {
      showToast('Reconnecting…', 'warning');
      return;
    }

    chatWs.send(JSON.stringify({ type: 'chat_message', content }));
    messageInput.value = '';
    autoResize();
    stopTyping();
  }

  sendBtn.addEventListener('click', sendMessage);

  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // ── Typing events ─────────────────────────────────────────────
  messageInput.addEventListener('input', () => {
    autoResize();
    if (!isTyping) {
      isTyping = true;
      sendTyping(true);
    }
    clearTimeout(typingTimeout);
    typingTimeout = setTimeout(stopTyping, 2000);
  });

  function sendTyping(state) {
    if (chatWs && chatWs.readyState === WebSocket.OPEN) {
      chatWs.send(JSON.stringify({ type: 'typing', is_typing: state }));
    }
  }

  function stopTyping() {
    if (isTyping) {
      isTyping = false;
      sendTyping(false);
    }
    clearTimeout(typingTimeout);
  }

  // ── Auto resize textarea ──────────────────────────────────────
  function autoResize() {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
  }

  // ── File handling ─────────────────────────────────────────────
  attachBtn.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      showToast('File too large (max 10MB)', 'error');
      return;
    }
    pendingFile = file;
    filePreviewName.textContent = file.name;

    if (file.type.startsWith('image/')) {
      filePreviewImg.style.display = 'block';
      filePreviewImg.src = URL.createObjectURL(file);
    } else {
      filePreviewImg.style.display = 'none';
    }
    filePreview.style.display = 'block';
    fileInput.value = '';
  });

  cancelFileBtn.addEventListener('click', () => {
    pendingFile = null;
    filePreview.style.display = 'none';
    filePreviewImg.src = '';
  });

  function sendFile() {
    if (!pendingFile) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      if (chatWs && chatWs.readyState === WebSocket.OPEN) {
        chatWs.send(JSON.stringify({
          type: 'file_message',
          file_data: e.target.result,
          file_name: pendingFile.name,
          file_type: pendingFile.type,
        }));
        pendingFile = null;
        filePreview.style.display = 'none';
        filePreviewImg.src = '';
      }
    };
    reader.readAsDataURL(pendingFile);
  }

  // ── Helpers ───────────────────────────────────────────────────
  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function truncate(str, n) {
    return str.length > n ? str.slice(0, n) + '…' : str;
  }

  function showToast(msg, type = 'info') {
    const toast = document.createElement('div');
    toast.style.cssText = `
      position:fixed; bottom:80px; left:50%; transform:translateX(-50%);
      background:var(--bg-raised); border:1px solid var(--border);
      color:var(--text-primary); padding:10px 20px; border-radius:8px;
      font-size:13px; z-index:9999; box-shadow:var(--shadow-md);
      animation: fadeInUp 200ms ease;
    `;
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
  }

})();
