/* ═══════════════════════════════════════════════════
   RakshakAI — script.js
   Handles: sidebar, chat CRUD, streaming, markdown
═══════════════════════════════════════════════════ */

// ── State ─────────────────────────────────────────
let currentSessionId = null;
let isStreaming = false;

// ── DOM refs ──────────────────────────────────────
const sidebar = document.getElementById("sidebar");
const sidebarOverlay = document.getElementById("sidebarOverlay");
const sidebarClose = document.getElementById("sidebarClose");
const hamburger = document.getElementById("hamburger");
const chatList = document.getElementById("chatList");
const newChatBtn = document.getElementById("newChatBtn");
const messagesWrap = document.getElementById("messagesWrap");
const messagesEl = document.getElementById("messages");
const welcome = document.getElementById("welcome");
const suggestionsArea = document.getElementById("suggestionsArea");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const topbarTitle = document.getElementById("topbarTitle");
const statsBtn = document.getElementById("statsBtn");
const resetBtn = document.getElementById("resetBtn");
const statsBar = document.getElementById("statsBar");
const statsText = document.getElementById("statsText");

// ══════════════════════════════════════════════════
// SIDEBAR TOGGLE
// ══════════════════════════════════════════════════

function openSidebar() {
  sidebar.classList.add("open");
  sidebarOverlay.classList.add("open");
}

function closeSidebar() {
  sidebar.classList.remove("open");
  sidebarOverlay.classList.remove("open");
}

hamburger.addEventListener("click", openSidebar);
sidebarClose.addEventListener("click", closeSidebar);
sidebarOverlay.addEventListener("click", closeSidebar);

// ══════════════════════════════════════════════════
// CHAT LIST — load from MongoDB
// ══════════════════════════════════════════════════

async function loadChatList() {
  try {
    const res = await fetch("/api/chats");
    const data = await res.json();
    renderChatList(data.chats || []);
  } catch (err) {
    console.error("Failed to load chats:", err);
  }
}

function renderChatList(chats) {
  chatList.innerHTML = "";

  if (!chats.length) {
    chatList.innerHTML = '<li class="chat-list-empty">No chats yet</li>';
    return;
  }

  chats.forEach((chat) => {
    const li = document.createElement("li");
    li.className =
      "chat-item" + (chat.id === currentSessionId ? " active" : "");
    li.dataset.id = chat.id;

    const time = formatTime(chat.updated_at);

    li.innerHTML = `
      <span class="chat-item-icon">💬</span>
      <div class="chat-item-body">
        <span class="chat-item-title">${escapeHtml(chat.title || "New Chat")}</span>
        <span class="chat-item-time">${time}</span>
      </div>
      <button class="chat-item-delete" title="Delete chat" data-id="${chat.id}">🗑</button>
    `;

    // Click item → switch chat
    li.addEventListener("click", (e) => {
      if (e.target.closest(".chat-item-delete")) return;
      switchChat(chat.id, chat.title);
    });

    // Delete button
    li.querySelector(".chat-item-delete").addEventListener("click", (e) => {
      e.stopPropagation();
      deleteChat(chat.id);
    });

    chatList.appendChild(li);
  });
}

function formatTime(isoStr) {
  if (!isoStr) return "";
  const d = new Date(isoStr);
  const now = new Date();
  const diffMs = now - d;
  const diffMin = Math.floor(diffMs / 60000);
  const diffH = Math.floor(diffMs / 3600000);
  const diffD = Math.floor(diffMs / 86400000);

  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffH < 24) return `${diffH}h ago`;
  if (diffD === 1) return "yesterday";
  if (diffD < 7) return `${diffD}d ago`;
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

function setActiveChatItem(sessionId) {
  document.querySelectorAll(".chat-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.id === sessionId);
  });
}

// ══════════════════════════════════════════════════
// NEW CHAT
// ══════════════════════════════════════════════════

newChatBtn.addEventListener("click", startNewChat);

async function startNewChat() {
  if (isStreaming) return;
  clearChat();
  currentSessionId = null;
  topbarTitle.textContent = "RakshakAI";
  setActiveChatItem(null);
  userInput.focus();
  closeSidebar();
}

// ══════════════════════════════════════════════════
// SWITCH CHAT — load history from MongoDB
// ══════════════════════════════════════════════════

async function switchChat(sessionId, title) {
  if (isStreaming || sessionId === currentSessionId) return;

  closeSidebar();
  clearChat();
  currentSessionId = sessionId;
  topbarTitle.textContent = title || "Chat";
  setActiveChatItem(sessionId);
  welcome.style.display = "none";

  try {
    const res = await fetch("/api/history", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    const data = await res.json();

    if (data.history && data.history.length > 0) {
      data.history.forEach((msg) => {
        appendBubble(msg.role === "user" ? "user" : "ai", msg.content);
      });
      scrollToBottom();
    } else {
      welcome.style.display = "flex";
    }
  } catch (err) {
    console.error("Failed to load history:", err);
  }
}

// ══════════════════════════════════════════════════
// DELETE CHAT
// ══════════════════════════════════════════════════

async function deleteChat(sessionId) {
  if (!confirm("Delete this chat?")) return;

  try {
    await fetch(`/api/chats/${sessionId}`, { method: "DELETE" });

    // If deleted current chat → reset to new
    if (sessionId === currentSessionId) {
      await startNewChat();
    }

    await loadChatList();
  } catch (err) {
    console.error("Delete failed:", err);
  }
}

// ══════════════════════════════════════════════════
// SEND MESSAGE
// ══════════════════════════════════════════════════

sendBtn.addEventListener("click", sendMessage);
userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// Auto-resize textarea
userInput.addEventListener("input", () => {
  userInput.style.height = "auto";
  userInput.style.height = Math.min(userInput.scrollHeight, 140) + "px";
});

// Suggestion chips
document.querySelectorAll(".chip").forEach((btn) => {
  btn.addEventListener("click", () => {
    userInput.value = btn.dataset.q;
    sendMessage();
  });
});

async function sendMessage() {
  const text = userInput.value.trim();
  if (!text || isStreaming) return;

  // Hide welcome / chips
  welcome.style.display = "none";
  suggestionsArea.style.display = "none";

  // Render user bubble
  appendBubble("user", text);
  userInput.value = "";
  userInput.style.height = "auto";
  scrollToBottom();

  // Typing indicator
  const typingRow = appendTyping();
  setStreaming(true);

  let aiBubble = null;
  let fullResponse = "";

  try {
    const evtSource = new EventSource("/api/chat?" + new URLSearchParams());

    // We use fetch + ReadableStream for POST-based SSE
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        session_id: currentSessionId,
      }),
    });

    evtSource.close(); // close dummy

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop(); // keep partial line

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (!raw) continue;

        let payload;
        try {
          payload = JSON.parse(raw);
        } catch {
          continue;
        }

        if (payload.type === "session") {
          currentSessionId = payload.session_id;
          if (payload.title) topbarTitle.textContent = payload.title;
        }

        if (payload.type === "chunk") {
          if (!aiBubble) {
            typingRow.remove();
            aiBubble = appendBubble("ai", "");
          }
          fullResponse += payload.content;
          aiBubble.querySelector(".bubble").innerHTML =
            renderMarkdown(fullResponse);
          scrollToBottom();
        }

        if (payload.type === "done") {
          if (aiBubble) {
            const meta = aiBubble.querySelector(".bubble-meta");
            if (meta)
              meta.textContent = `${payload.stats?.total_tokens || 0} tokens · ${new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}`;
          }
          await loadChatList(); // refresh sidebar
        }

        if (payload.type === "error") {
          typingRow.remove();
          appendBubble("ai", `⚠️ ${payload.message}`);
        }
      }
    }
  } catch (err) {
    typingRow?.remove();
    appendBubble("ai", `⚠️ Network error: ${err.message}`);
  } finally {
    setStreaming(false);
    scrollToBottom();
  }
}

// ══════════════════════════════════════════════════
// BUBBLE HELPERS
// ══════════════════════════════════════════════════

function appendBubble(role, text) {
  const isUser = role === "user";
  const row = document.createElement("div");
  row.className = `bubble-row ${role}`;

  const time = new Date().toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
  });

  row.innerHTML = `
    <div class="avatar ${isUser ? "user" : "ai"}">${isUser ? "👤" : "⚖️"}</div>
    <div>
      <div class="bubble ${isUser ? "user" : "ai"}">${isUser ? escapeHtml(text) : renderMarkdown(text)}</div>
      <div class="bubble-meta">${time}</div>
    </div>
  `;

  messagesEl.appendChild(row);
  return row;
}

function appendTyping() {
  const row = document.createElement("div");
  row.className = "bubble-row ai";
  row.innerHTML = `
    <div class="avatar ai">⚖️</div>
    <div>
      <div class="bubble ai">
        <div class="typing"><span></span><span></span><span></span></div>
      </div>
    </div>
  `;
  messagesEl.appendChild(row);
  scrollToBottom();
  return row;
}

function clearChat() {
  messagesEl.innerHTML = "";
  welcome.style.display = "flex";
  suggestionsArea.style.display = "";
  statsBar.style.display = "none";
}

function scrollToBottom() {
  messagesWrap.scrollTop = messagesWrap.scrollHeight;
}

function setStreaming(val) {
  isStreaming = val;
  sendBtn.disabled = val;
  userInput.disabled = val;
}

// ══════════════════════════════════════════════════
// STATS
// ══════════════════════════════════════════════════

statsBtn.addEventListener("click", async () => {
  try {
    const res = await fetch("/api/stats");
    const data = await res.json();
    statsText.textContent = `Sessions: ${data.total_sessions} · Messages: ${data.total_messages}`;
    statsBar.style.display = "flex";
  } catch {}
});

// ══════════════════════════════════════════════════
// RESET current chat
// ══════════════════════════════════════════════════

resetBtn.addEventListener("click", async () => {
  if (!currentSessionId) {
    clearChat();
    return;
  }
  if (!confirm("Clear this conversation?")) return;
  try {
    await fetch("/api/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSessionId }),
    });
    clearChat();
    await loadChatList();
  } catch {}
});

// ══════════════════════════════════════════════════
// MARKDOWN (lightweight, no dependency)
// ══════════════════════════════════════════════════

function renderMarkdown(text) {
  if (!text) return "";
  let html = escapeHtml(text);

  // Code blocks
  html = html.replace(
    /```[\w]*\n?([\s\S]*?)```/g,
    "<pre><code>$1</code></pre>",
  );
  // Inline code
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  // Italic
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
  // Headers
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");
  // Blockquote
  html = html.replace(/^&gt; (.+)$/gm, "<blockquote>$1</blockquote>");
  // Unordered list
  html = html.replace(/^\* (.+)$/gm, "<li>$1</li>");
  html = html.replace(/^- (.+)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>\n?)+/g, (s) => `<ul>${s}</ul>`);
  // Numbered list
  html = html.replace(/^\d+\. (.+)$/gm, "<li>$1</li>");
  // Paragraphs
  html = html.replace(/\n\n+/g, "</p><p>");
  html = html.replace(/\n/g, "<br>");
  if (!html.startsWith("<")) html = "<p>" + html + "</p>";

  return html;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ══════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════

loadChatList();
