import asyncio
import json
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import DefaultDict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.websockets import WebSocketState
from fastapi.responses import HTMLResponse
from redis.asyncio import Redis

REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
HISTORY_LIMIT = 100
CHANNEL_PREFIX = "chat:"
HISTORY_PREFIX = "chat_history:"

redis_client: Redis | None = None
subscriber_task: asyncio.Task | None = None
connections_by_channel: DefaultDict[str, list[WebSocket]] = defaultdict(list)


HTML_PAGE = r'''<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Cosmic Realtime Chat</title>
  <style>
    :root {
      --bg1: #060816;
      --bg2: #0a1030;
      --panel: rgba(14, 20, 45, 0.72);
      --panel-border: rgba(150, 180, 255, 0.18);
      --text: #eef3ff;
      --muted: #9fb0da;
      --primary: #7c5cff;
      --primary-2: #25d0ff;
      --success: #7dffbf;
      --danger: #ff8ab6;
      --input: rgba(255,255,255,0.06);
      --shadow: 0 20px 60px rgba(0,0,0,0.45);
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 15% 20%, rgba(124, 92, 255, 0.28), transparent 24%),
        radial-gradient(circle at 85% 18%, rgba(37, 208, 255, 0.20), transparent 20%),
        radial-gradient(circle at 50% 80%, rgba(116, 69, 255, 0.18), transparent 28%),
        linear-gradient(160deg, var(--bg1), var(--bg2));
      overflow: hidden;
    }

    .stars, .stars:before, .stars:after {
      content: "";
      position: fixed;
      inset: 0;
      background-image:
        radial-gradient(2px 2px at 20px 30px, rgba(255,255,255,0.85), transparent),
        radial-gradient(1px 1px at 140px 80px, rgba(255,255,255,0.65), transparent),
        radial-gradient(1.5px 1.5px at 280px 160px, rgba(37,208,255,0.8), transparent),
        radial-gradient(1px 1px at 420px 220px, rgba(124,92,255,0.8), transparent),
        radial-gradient(2px 2px at 680px 120px, rgba(255,255,255,0.7), transparent);
      background-size: 720px 360px;
      animation: drift 80s linear infinite;
      pointer-events: none;
      opacity: 0.55;
    }
    .stars:before { animation-duration: 120s; opacity: 0.35; }
    .stars:after { animation-duration: 160s; opacity: 0.2; }

    @keyframes drift {
      from { transform: translateY(0); }
      to { transform: translateY(-360px); }
    }

    .shell {
      position: relative;
      z-index: 1;
      max-width: 1180px;
      margin: 0 auto;
      min-height: 100vh;
      padding: 32px 20px;
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 22px;
    }

    .card {
      background: var(--panel);
      border: 1px solid var(--panel-border);
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
      border-radius: 24px;
      box-shadow: var(--shadow);
    }

    .sidebar {
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 14px;
      margin-bottom: 6px;
    }

    .planet {
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: linear-gradient(135deg, var(--primary), var(--primary-2));
      position: relative;
      box-shadow: 0 0 40px rgba(124, 92, 255, 0.55);
      flex: none;
    }

    .planet:after {
      content: "";
      position: absolute;
      inset: 22px -10px auto -10px;
      height: 14px;
      border: 2px solid rgba(255,255,255,0.55);
      border-radius: 999px;
      transform: rotate(-18deg);
    }

    h1 {
      margin: 0;
      font-size: 28px;
      line-height: 1.1;
      letter-spacing: -0.03em;
    }

    .subtitle {
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }

    .field {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .field label {
      font-size: 13px;
      color: var(--muted);
      font-weight: 600;
      letter-spacing: 0.02em;
    }

    .input {
      width: 100%;
      border: 1px solid rgba(255,255,255,0.1);
      background: var(--input);
      color: var(--text);
      border-radius: 16px;
      padding: 14px 16px;
      font-size: 15px;
      outline: none;
      transition: 0.2s ease;
    }

    .input:focus {
      border-color: rgba(124, 92, 255, 0.8);
      box-shadow: 0 0 0 4px rgba(124, 92, 255, 0.15);
    }

    .btn {
      border: 0;
      border-radius: 16px;
      padding: 14px 16px;
      font-size: 15px;
      font-weight: 700;
      color: white;
      cursor: pointer;
      transition: transform 0.15s ease, box-shadow 0.2s ease, opacity 0.2s ease;
    }

    .btn:hover { transform: translateY(-1px); }
    .btn:active { transform: translateY(0); }
    .btn:disabled { opacity: 0.55; cursor: not-allowed; }

    .btn-primary {
      background: linear-gradient(135deg, var(--primary), var(--primary-2));
      box-shadow: 0 10px 30px rgba(73, 129, 255, 0.28);
    }

    .btn-secondary {
      background: linear-gradient(135deg, rgba(255,255,255,0.14), rgba(255,255,255,0.08));
      border: 1px solid rgba(255,255,255,0.12);
    }

    .status {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 14px 16px;
      border-radius: 18px;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.08);
      font-size: 14px;
      color: var(--muted);
    }

    .dot {
      width: 12px;
      height: 12px;
      border-radius: 999px;
      background: var(--danger);
      box-shadow: 0 0 12px rgba(255, 138, 182, 0.5);
      flex: none;
    }

    .dot.connected {
      background: var(--success);
      box-shadow: 0 0 12px rgba(125, 255, 191, 0.55);
    }

    .meta {
      margin-top: auto;
      padding: 16px;
      border-radius: 18px;
      background: linear-gradient(135deg, rgba(124, 92, 255, 0.16), rgba(37, 208, 255, 0.12));
      border: 1px solid rgba(255,255,255,0.1);
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
    }

    .main {
      padding: 22px;
      display: grid;
      grid-template-rows: auto 1fr auto;
      min-height: calc(100vh - 64px);
      gap: 18px;
    }

    .toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      padding: 8px 6px 2px;
    }

    .toolbar h2 {
      margin: 0;
      font-size: 20px;
      letter-spacing: -0.02em;
    }

    .toolbar p {
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 13px;
    }

    .messages {
      overflow-y: auto;
      padding-right: 6px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      min-height: 0;
    }

    .message {
      max-width: 78%;
      padding: 14px 16px;
      border-radius: 20px;
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.09);
      box-shadow: 0 8px 24px rgba(0,0,0,0.2);
    }

    .message.mine {
      margin-left: auto;
      background: linear-gradient(135deg, rgba(124, 92, 255, 0.32), rgba(37, 208, 255, 0.20));
      border-color: rgba(124, 92, 255, 0.3);
    }

    .message-header {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 8px;
    }

    .message-body {
      font-size: 15px;
      line-height: 1.6;
      word-break: break-word;
    }

    .composer {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: center;
      padding-top: 4px;
    }

    .composer .input {
      padding: 16px 18px;
      border-radius: 18px;
    }

    .empty {
      margin: auto;
      text-align: center;
      color: var(--muted);
      padding: 40px 20px;
      border: 1px dashed rgba(255,255,255,0.15);
      border-radius: 22px;
      background: rgba(255,255,255,0.03);
    }

    @media (max-width: 980px) {
      body { overflow: auto; }
      .shell {
        grid-template-columns: 1fr;
        min-height: auto;
      }
      .main { min-height: 68vh; }
      .message { max-width: 100%; }
    }
  </style>
</head>
<body>
  <div class="stars"></div>
  <div class="shell">
    <aside class="card sidebar">
      <div class="brand">
        <div class="planet"></div>
        <div>
          <h1>Cosmic Chat</h1>
          <p class="subtitle">FastAPI · Redis Pub/Sub · WebSocket 기반 실시간 채팅</p>
        </div>
      </div>

      <div class="field">
        <label for="room">ROOM</label>
        <input class="input" id="room" value="room1" placeholder="예: room1" />
      </div>

      <div class="field">
        <label for="sender">SENDER</label>
        <input class="input" id="sender" value="wataru" placeholder="예: wataru" />
      </div>

      <button class="btn btn-primary" id="connectBtn" type="button">연결 시작</button>
      <button class="btn btn-secondary" id="disconnectBtn" type="button" disabled>연결 종료</button>

      <div class="status">
        <span class="dot" id="statusDot"></span>
        <span id="statusText">대기 중</span>
      </div>

      <div class="meta">
        같은 Room으로 접속한 사용자끼리 메시지를 공유합니다.<br />
        Redis에는 최근 메시지 이력이 저장되고, 접속 시 자동으로 불러옵니다.
      </div>
    </aside>

    <main class="card main">
      <div class="toolbar">
        <div>
          <h2 id="roomTitle">room1</h2>
          <p id="roomDescription">연결 후 메시지를 주고받아 보세요.</p>
        </div>
      </div>

      <section class="messages" id="messages">
        <div class="empty" id="emptyState">아직 메시지가 없습니다. 우주 채팅을 시작해보세요.</div>
      </section>

      <div class="composer">
        <input class="input" id="message" type="text" placeholder="메시지를 입력하세요" />
        <button class="btn btn-primary" id="sendBtn" type="button" disabled>전송</button>
      </div>
    </main>
  </div>

  <script>
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
      return `${scheme}://${location.host}/ws/chat/${encodeURIComponent(room)}/${encodeURIComponent(sender)}`;
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
  </script>
</body>
</html>'''


def channel_name(room: str) -> str:
    return f"{CHANNEL_PREFIX}{room}"


def history_key(room: str) -> str:
    return f"{HISTORY_PREFIX}{room}"


async def init_redis() -> None:
    global redis_client
    redis_client = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    await redis_client.ping()
    print("✅ Redis 연결 완료")


async def close_redis() -> None:
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        print("🔌 Redis 연결 종료")


async def save_message(room: str, sender: str, message: str) -> str:
    assert redis_client is not None
    payload = {
        "room": room,
        "sender": sender,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    message_str = json.dumps(payload, ensure_ascii=False)
    await redis_client.rpush(history_key(room), message_str)
    await redis_client.ltrim(history_key(room), -HISTORY_LIMIT, -1)
    return message_str


async def publish_message(room: str, message_str: str) -> None:
    assert redis_client is not None
    await redis_client.publish(channel_name(room), message_str)


async def save_and_publish(room: str, sender: str, message: str) -> str:
    message_str = await save_message(room, sender, message)
    await publish_message(room, message_str)
    return message_str


async def get_history(room: str, start: int = 0, end: int = -1) -> list[str]:
    assert redis_client is not None
    return await redis_client.lrange(history_key(room), start, end)


async def register_ws(room: str, websocket: WebSocket) -> None:
    connections_by_channel[channel_name(room)].append(websocket)


async def unregister_ws(room: str, websocket: WebSocket) -> None:
    ch = channel_name(room)
    if websocket in connections_by_channel[ch]:
        connections_by_channel[ch].remove(websocket)
    if not connections_by_channel[ch]:
        connections_by_channel.pop(ch, None)


async def redis_subscriber() -> None:
    assert redis_client is not None
    pubsub = redis_client.pubsub()
    await pubsub.psubscribe(f"{CHANNEL_PREFIX}*")
    print("📡 Redis Pub/Sub 구독 시작")
    try:
        async for item in pubsub.listen():
            if item.get("type") != "pmessage":
                continue

            channel = item["channel"]
            data = item["data"]
            room_connections = connections_by_channel.get(channel, [])
            disconnected: list[WebSocket] = []

            for ws in room_connections:
                try:
                    await ws.send_text(data)
                except Exception:
                    disconnected.append(ws)

            for ws in disconnected:
                if ws in room_connections:
                    room_connections.remove(ws)
    except asyncio.CancelledError:
        await pubsub.punsubscribe(f"{CHANNEL_PREFIX}*")
        await pubsub.close()
        print("🛑 Redis Pub/Sub 구독 종료")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    global subscriber_task
    await init_redis()
    subscriber_task = asyncio.create_task(redis_subscriber())
    print("🚀 FastAPI + Redis Pub/Sub + WebSocket 시작")
    yield
    if subscriber_task is not None:
        subscriber_task.cancel()
        try:
            await subscriber_task
        except asyncio.CancelledError:
            pass
    await close_redis()
    print("👋 애플리케이션 종료")


app = FastAPI(title="Realtime Chat App", lifespan=lifespan)


@app.get("/")
async def home() -> HTMLResponse:
    return HTMLResponse(HTML_PAGE)


@app.get("/chat/history/{room}")
async def chat_history(room: str, start: int = Query(0), end: int = Query(-1)):
    messages = await get_history(room, start, end)
    return {"room": room, "count": len(messages), "messages": messages}


@app.websocket("/ws/chat/{room}/{sender}")
async def websocket_chat(websocket: WebSocket, room: str, sender: str):
    await websocket.accept()
    await register_ws(room, websocket)

    try:
        history = await get_history(room)
        for item in history:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(item)

        while True:
            text = await websocket.receive_text()
            if text.strip():
                await save_and_publish(room, sender, text.strip())
    except WebSocketDisconnect:
        await unregister_ws(room, websocket)
        print(f"❌ 연결 종료: room={room}, sender={sender}")
    except Exception as exc:
        await unregister_ws(room, websocket)
        print(f"❌ WebSocket 오류: {exc}")


@app.get("/health")
async def health():
    return {"status": "UP"}


# 실행 예시:
# uvicorn fastapi_redis_chat_app:app --reload
# Redis가 먼저 떠 있어야 함.
