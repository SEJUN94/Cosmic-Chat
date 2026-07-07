let ws = null;
let currentSender = '';

const roomInput = document.getElementById('room');
const senderInput = document.getElementById('sender');
const messageInput = document.getElementById('message');
const messagesEl = document.getElementById('messages');
const emptyState = document.getElementById('emptyState');
const connectBtn = document.getElementById('connectBtn');
const disconnectBtn = document.getElementById('disconnectBtn');
const sendBtn = document.getElementById('sendBtn');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const roomTitle = document.getElementById('roomTitle');
const roomDescription = document.getElementById('roomDescription');

function setStatus(text, connected) {
  statusText.textContent = text;
  statusDot.classList.toggle('connected', !!connected);
  sendBtn.disabled = !connected;
  disconnectBtn.disabled = !connected;
  connectBtn.disabled = !!connected;
}

function formatTime(value) {
  try {
    return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return value ?? '';
  }
}

function appendMessage(raw) {
  let data = raw;
  if (typeof raw === 'string') {
    try {
      data = JSON.parse(raw);
    } catch {
      data = { sender: 'system', message: raw, room: roomInput.value, timestamp: new Date().toISOString() };
    }
  }

  emptyState.style.display = 'none';

  const item = document.createElement('article');
  item.className = 'message';
  if (data.sender === currentSender) item.classList.add('mine');

  item.innerHTML = `
    <div class="message-header">
      <strong>${escapeHtml(data.sender ?? 'unknown')}</strong>
      <span>${escapeHtml(formatTime(data.timestamp))}</span>
    </div>
    <div class="message-body">${escapeHtml(data.message ?? '')}</div>
  `;

  messagesEl.appendChild(item);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function escapeHtml(str) {
  return String(str)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function resetMessages() {
  messagesEl.innerHTML = '';
  messagesEl.appendChild(emptyState);
  emptyState.style.display = 'block';
}

function getWsUrl(room, sender) {
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
  return `${scheme}://${location.host}/chat/ws/${encodeURIComponent(room)}/${encodeURIComponent(sender)}`;
}

function connectWs() {
  const room = roomInput.value.trim();
  const sender = senderInput.value.trim();

  if (!room || !sender) {
    setStatus('Room과 Sender를 입력하세요.', false);
    return;
  }

  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    ws.close();
  }

  resetMessages();
  currentSender = sender;
  roomTitle.textContent = room;
  roomDescription.textContent = `${sender} 님으로 연결 중입니다.`;
  setStatus('연결 중...', false);

  ws = new WebSocket(getWsUrl(room, sender));

  ws.onopen = () => {
    roomDescription.textContent = `${sender} 님이 ${room}에 연결되었습니다.`;
    setStatus('연결됨', true);
    messageInput.focus();
  };

  ws.onmessage = (event) => {
    appendMessage(event.data);
  };

  ws.onclose = () => {
    roomDescription.textContent = '연결이 종료되었습니다.';
    setStatus('연결 종료', false);
  };

  ws.onerror = () => {
    roomDescription.textContent = '연결 중 오류가 발생했습니다.';
    setStatus('연결 오류', false);
  };
}

function disconnectWs() {
  if (ws) {
    ws.close();
    ws = null;
  }
}

function sendMsg() {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    setStatus('먼저 연결을 시작하세요.', false);
    return;
  }

  const msg = messageInput.value.trim();
  if (!msg) return;

  ws.send(msg);
  messageInput.value = '';
  messageInput.focus();
}

connectBtn.addEventListener('click', connectWs);
disconnectBtn.addEventListener('click', disconnectWs);
sendBtn.addEventListener('click', sendMsg);
messageInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') sendMsg();
});

/*
// 페이지 로드되자마자 연결 버튼 자동 클릭
window.addEventListener('load', () => {
connectBtn.click();
});
*/

// ====================== 자동 연결 기능 추가 ======================
window.addEventListener('DOMContentLoaded', () => {
    // 기본값 자동 설정 (index.html에서 세팅을 해주고 있으나 비어있다면 아래에서 세팅)
    if (!roomInput.value.trim()) {
        roomInput.value = 'Cosmic talk';        // 기본 방 이름
    }
    if (!senderInput.value.trim()) {
        senderInput.value = '최혁명';        // 기본 발신자 이름 (테스트용)
        // 실제 서비스라면 로그인한 사용자 이름으로 설정하는 게 좋습니다.
    }

    // 자동 연결 실행
    console.log("🔌 페이지 로드 → 자동 연결 시도");
    connectWs();
});
// ============================================================