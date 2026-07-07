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

/*
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

  // ⭐⭐⭐ 핵심: 다른 사람이 보낸 메시지만 소리 재생
  if (data.sender && data.sender !== currentSender) {
    playNotificationSound();
  }

  // 스크롤 자동 이동 (부드럽게)
  messagesEl.scrollTo({
    top: messagesEl.scrollHeight,
    behavior: 'smooth'
  });
}
*/

// ==================== appendMessage 함수 전체 교체 ====================
function appendMessage(raw) {
  let data = raw;
  if (typeof raw === 'string') {
    try {
      data = JSON.parse(raw);
    } catch {
      data = { sender: 'system', message: raw, timestamp: new Date().toISOString() };
    }
  }

  emptyState.style.display = 'none';

  const item = document.createElement('article');
  item.className = 'message';
  if (data.sender === currentSender) item.classList.add('mine');

  if (data.type === 'image' && data.image) {
    // 사진 메시지
    item.classList.add('image');
    item.innerHTML = `
      <div class="message-header">
        <strong>${escapeHtml(data.sender ?? 'unknown')}</strong>
        <span>${escapeHtml(formatTime(data.timestamp))}</span>
      </div>
      <div class="message-body">
        ${data.message ? `<p>${escapeHtml(data.message)}</p>` : ''}
        <img src="${data.image}" alt="전송된 사진" />
      </div>
    `;
  } else {
    // 일반 텍스트 메시지
    item.innerHTML = `
      <div class="message-header">
        <strong>${escapeHtml(data.sender ?? 'unknown')}</strong>
        <span>${escapeHtml(formatTime(data.timestamp))}</span>
      </div>
      <div class="message-body">${escapeHtml(data.message ?? data.text ?? '')}</div>
    `;
  }

  messagesEl.appendChild(item);

  // 다른 사람이 보낸 메시지면 소리 재생
  if (data.sender && data.sender !== currentSender) {
    playNotificationSound();
  }

  // 자동 스크롤
  messagesEl.scrollTo({
    top: messagesEl.scrollHeight,
    behavior: 'smooth'
  });
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
    const data = JSON.parse(event.data);

    if (data.type === 'message' || data.type === 'chat') {   // 백엔드에서 오는 타입에 맞게
      addMessage(data);
    }
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
/*
// 스크롤을 가장 아래로 이동시키는 함수
function scrollToBottom() {
  const messagesContainer = document.getElementById('messages');
  if (messagesContainer) {
    // 부드럽게 스크롤 (더 자연스러움)
    messagesContainer.scrollTo({
      top: messagesContainer.scrollHeight,
      behavior: 'smooth'
    });
  }
}

// ✅ 메시지를 추가하는 모든 곳에서 이 함수를 호출하세요
// 예시:
function addMessage(messageData) {
  const messages = document.getElementById('messages');
  
  // empty state 숨기기
  const emptyState = document.getElementById('emptyState');
  if (emptyState) emptyState.style.display = 'none';
  
  // 메시지 DOM 생성 (기존 코드에 맞게)
  const msgDiv = document.createElement('div');
  // ... 당신의 메시지 스타일링 코드 ...
  
  messages.appendChild(msgDiv);
  
  // ⭐⭐⭐ 새 메시지 올 때마다 자동 스크롤
  scrollToBottom();
}
*/

// WebSocket으로 메시지 받을 때도 동일하게 호출
// 예: socket.onmessage = (event) => { ... addMessage(...) }

// 처음 페이지 로드 시 이전 메시지 불러온 후에도 호출
window.addEventListener('load', () => {
  // 기존 메시지 로드 로직이 끝난 뒤
  scrollToBottom();
});

// ==================== 알림 소리 관련 ====================

// AudioContext (한 번만 생성)
let audioContext = null;

//Cosmic Chime (가장 추천 - 우주 느낌 부드러운 종소리)
function playNotificationSound() {
  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }

  const now = audioContext.currentTime;
  const durations = [0.35, 0.45, 0.55];

  // 낮은 톤 → 중간 → 높은 톤으로 우주스러운 멜로디
  [620, 820, 1100].forEach((freq, i) => {
    setTimeout(() => {
      const osc = audioContext.createOscillator();
      const gain = audioContext.createGain();
      
      osc.connect(gain);
      gain.connect(audioContext.destination);
      
      osc.frequency.setValueAtTime(freq, now + i * 0.08);
      gain.gain.setValueAtTime(0.4, now + i * 0.08);
      gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.08 + durations[i]);
      
      osc.start(now + i * 0.08);
      osc.stop(now + i * 0.08 + durations[i] + 0.1);
    }, i * 80);
  });
}

/*
// 알림 소리 재생 함수 (부드러운 '딩~' 소리)
function playNotificationSound1() {
  // 브라우저 정책 때문에 처음엔 사용자 인터랙션이 필요합니다 (연결 시작 or 메시지 전송하면 OK)
  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }

  // 간단하지만 예쁜 알림음 만들기
  const now = audioContext.currentTime;

  // 첫 번째 톤
  const osc1 = audioContext.createOscillator();
  const gain1 = audioContext.createGain();
  osc1.connect(gain1);
  gain1.connect(audioContext.destination);
  osc1.frequency.setValueAtTime(800, now);
  gain1.gain.setValueAtTime(0.3, now);
  gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
  osc1.start(now);
  osc1.stop(now + 0.3);

  // 두 번째 높은 톤 (딩~ 느낌)
  setTimeout(() => {
    const osc2 = audioContext.createOscillator();
    const gain2 = audioContext.createGain();
    osc2.connect(gain2);
    gain2.connect(audioContext.destination);
    osc2.frequency.setValueAtTime(1200, now + 0.05);
    gain2.gain.setValueAtTime(0.3, now + 0.05);
    gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
    osc2.start(now + 0.05);
    osc2.stop(now + 0.35);
  }, 50);
}
*/

//Classic Modern Ding (깔끔하고 선명한 알림음)
function playNotificationSound2() {
  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }

  const now = audioContext.currentTime;

  // 메인 딩
  const osc1 = audioContext.createOscillator();
  const gain1 = audioContext.createGain();
  osc1.frequency.setValueAtTime(880, now);     // 높은 피아노 소리
  gain1.gain.setValueAtTime(0.5, now);
  gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.6);
  osc1.connect(gain1).connect(audioContext.destination);
  osc1.start(now);
  osc1.stop(now + 0.7);

  // 잔향 (echo 느낌)
  setTimeout(() => {
    const osc2 = audioContext.createOscillator();
    const gain2 = audioContext.createGain();
    osc2.frequency.setValueAtTime(1100, now + 0.1);
    gain2.gain.setValueAtTime(0.25, now + 0.1);
    gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.45);
    osc2.connect(gain2).connect(audioContext.destination);
    osc2.start(now + 0.1);
    osc2.stop(now + 0.55);
  }, 100);
}

//Soft Bell (부드럽고 잔잔한 종소리)
function playNotificationSound3() {
  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }

  const now = audioContext.currentTime;
  const freqs = [740, 880, 990];

  freqs.forEach((freq, i) => {
    const osc = audioContext.createOscillator();
    const gain = audioContext.createGain();
    osc.frequency.setValueAtTime(freq, now + i * 0.03);
    gain.gain.setValueAtTime(0.35, now + i * 0.03);
    gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.03 + 0.8);

    osc.connect(gain).connect(audioContext.destination);
    osc.start(now + i * 0.03);
    osc.stop(now + i * 0.03 + 1);
  });
}

// ==================== 메시지 추가 시 소리 재생 ====================

// 기존 addMessage 함수가 있다면 아래처럼 수정 (또는 새로 만들기)
function addMessage(data) {
  const messages = document.getElementById('messages');
  const currentSender = document.getElementById('sender').value.trim();

  // empty state 숨기기
  const emptyState = document.getElementById('emptyState');
  if (emptyState) emptyState.style.display = 'none';

  // 메시지 DOM 생성 (기존 코드 그대로 사용)
  const messageEl = document.createElement('div');
  // ... 당신의 기존 메시지 스타일링 코드 ...

  messages.appendChild(messageEl);

  // ⭐⭐⭐ 핵심: 자기 자신이 보낸 메시지가 아닐 때만 소리 재생
  if (data.sender && data.sender !== currentSender) {
    playNotificationSound3();
  }

  // 자동 스크롤 (이전 응답에서 준 함수)
  scrollToBottom();
}

// ==================== 사진 전송 관련 변수 추가 ====================
const imageInput = document.getElementById('imageInput');
const attachBtn = document.getElementById('attachBtn');

// 첨부 버튼 클릭 → 파일 선택 창 열기
attachBtn.addEventListener('click', () => {
  imageInput.click();
});

// 파일 선택 시 바로 전송
imageInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;

  // 이미지 크기 제한 (10MB)
  if (file.size > 10 * 1024 * 1024) {
    alert('10MB 이하의 이미지만 전송할 수 있습니다.');
    imageInput.value = '';
    return;
  }

  const reader = new FileReader();
  reader.onload = function (ev) {
    const base64 = ev.target.result; // data:image/jpeg;base64,....

    const caption = messageInput.value.trim();

    // JSON 형태로 전송 (텍스트 + 사진 같이 가능)
    const payload = {
      type: 'image',
      sender: currentSender,
      message: caption || '사진',
      image: base64,
      timestamp: new Date().toISOString()
    };

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
      messageInput.value = '';        // 입력창 비우기
      imageInput.value = '';          // 파일 초기화
    } else {
      alert('먼저 연결을 시작해주세요.');
    }
  };
  reader.readAsDataURL(file);
});