import asyncio
import json
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import DefaultDict
from app.core.config import get_settings

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Query, APIRouter
from fastapi.templating import Jinja2Templates   # ← 추가
from fastapi.websockets import WebSocketState
from fastapi.responses import HTMLResponse
from redis.asyncio import Redis


router = APIRouter(prefix="/chat", tags=["chat"])

settings = get_settings()

redis_client: Redis | None = None
#subscriber_task: asyncio.Task | None = None
#connections_by_channel: DefaultDict[str, list[WebSocket]] = defaultdict(list)
# 전역 변수들 (실무에서는 dependency injection으로 개선 가능)
connections_by_channel = defaultdict(list)
#redis_client = None   # main.py에서 주입받을 예정
templates = Jinja2Templates(directory="app/templates")


def channel_name(room: str) -> str:
    return f"{settings.CHANNEL_PREFIX}{room}"


def history_key(room: str) -> str:
    return f"{settings.HISTORY_PREFIX}{room}"


async def init_chat_redis() -> None:
    global redis_client
    redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)
    await redis_client.ping()
    print("✅ Redis 연결 완료")


async def close_chat_redis() -> None:
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        print("🔌 Redis 연결 종료")


async def save_message(room: str, sender: str, payload: dict) -> str:
    assert redis_client is not None
    
    # payload가 문자열인 경우(기존 방식)도 처리
    if isinstance(payload, str):
        payload = {"message": payload}

    full_payload = {
        "room": room,
        "sender": sender,
        "type": payload.get("type", "text"),           # ← 추가
        "message": payload.get("message") or payload.get("text", ""),
        "image": payload.get("image"),                 # ← 사진 추가
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    message_str = json.dumps(full_payload, ensure_ascii=False)
    await redis_client.rpush(history_key(room), message_str)
    await redis_client.ltrim(history_key(room), -settings.HISTORY_LIMIT, -1)
    return message_str


async def publish_message(room: str, message_str: str) -> None:
    assert redis_client is not None
    await redis_client.publish(channel_name(room), message_str)


async def save_and_publish(room: str, sender: str, payload: dict | str) -> str:
    message_str = await save_message(room, sender, payload)
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
    await pubsub.psubscribe(f"{settings.CHANNEL_PREFIX}*")
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
        await pubsub.punsubscribe(f"{settings.CHANNEL_PREFIX}*")
        await pubsub.close()
        print("🛑 Redis Pub/Sub 구독 종료")
        raise

@router.get("/")
async def home(request: Request,):
    #return templates.TemplateResponse("index.html", {"request": request})
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "title": "Cosmic Chat",
        }
    )


@router.get("/history/{room}")
async def chat_history(room: str, start: int = Query(0), end: int = Query(-1)):
    messages = await get_history(room, start, end)
    return {"room": room, "count": len(messages), "messages": messages}


@router.websocket("/ws/{room}/{sender}")
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
            if not text.strip():
                continue

            try:
                # JSON으로 온 경우 (사진 포함)
                data = json.loads(text)
            except json.JSONDecodeError:
                # 기존 방식 (일반 텍스트)
                data = {"message": text.strip()}

            # sender 정보 추가
            data["sender"] = sender

            await save_and_publish(room, sender, data)
    except WebSocketDisconnect:
        await unregister_ws(room, websocket)
        print(f"❌ 연결 종료: room={room}, sender={sender}")
    except Exception as exc:
        await unregister_ws(room, websocket)
        print(f"❌ WebSocket 오류: {exc}")


@router.get("/health")
async def health():
    return {"status": "UP"}


# 실행 예시:
# uvicorn fastapi_redis_chat_app:app --reload
# Redis가 먼저 떠 있어야 함.
