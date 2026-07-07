from redis.asyncio import Redis, ConnectionPool
from app.core.config import get_settings
import json
import asyncio
from datetime import datetime

settings = get_settings()

# 전역 Redis 클라이언트
redis_pool: ConnectionPool | None = None

# Pub/Sub Task 관리용 전역 변수
redis_client: Redis | None = None


async def init_redis():
    """Redis 연결 초기화"""
    global redis_pool, redis_client
    redis_pool = ConnectionPool.from_url(
        settings.REDIS_URL,            # .env에서 가져오는 방식 그대로 유지
        max_connections=30,
        decode_responses=True,
        # 🔥 Pub/Sub에서 반드시 필요한 설정들
        socket_timeout=None,           # ← 핵심! Timeout 제거
        socket_connect_timeout=10,
        socket_keepalive=True,         # 연결 유지
        retry_on_timeout=True,
        health_check_interval=30
    )
    redis_client = Redis(connection_pool=redis_pool)
    print("🚀 Redis 연결 풀 초기화 완료")

async def close_redis():
    """Redis 연결 종료"""
    global redis_client, redis_pool
    if redis_client:
        await redis_client.aclose()
    if redis_pool:
        await redis_pool.aclose()
    print("🛑 Redis 연결 종료")

# ==================== 실무 헬퍼 함수 ====================

# 1. 캐싱
async def set_value(key: str, value: any, expire: int = 3600):
    """Redis에 값 저장 / 일반 캐싱 (String, JSON 등 / expire: 초 단위, 기본 1시간)"""
    if redis_client is None:
        raise RuntimeError("Redis가 초기화되지 않았습니다.")
    
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
        
    await redis_client.set(key, value, ex=expire)
    print(f"✅ Redis SET 성공 → {key} (expire: {expire}s)")

async def get_value(key: str):
    """Redis에서 값 가져오기 / 캐싱 조회"""
    if redis_client is None:
        raise RuntimeError("Redis가 초기화되지 않았습니다.")
    
    value = await redis_client.get(key)

    if value is None:
        return None
    
    # JSON 형태이면 자동 변환
    if value and (value.startswith('{') or value.startswith('[')):
        return json.loads(value)
    return value

async def delete_value(key: str):
    """Redis에서 값 삭제"""
    if redis_client is None:
        raise RuntimeError("Redis가 초기화되지 않았습니다.")
    
    deleted = await redis_client.delete(key)
    print(f"🗑️ Redis DELETE → {key} ({deleted}개 삭제)")
    return deleted > 0

# 2. Pub/Sub 
# 단순 전송기능(휘발성)
async def publish_message(channel: str, message: str | dict):
    """Pub/Sub로 메시지 발행 (다른 구독자에게 전송)"""
    if redis_client is None:
        raise RuntimeError("Redis가 초기화되지 않았습니다.")
    
    if isinstance(message, dict):
        import json
        message_str = json.dumps(message, ensure_ascii=False)  # 한글 깨짐 방지
    else:
        message_str = str(message)   # str이거나 다른 타입이면 문자열로

    await redis_client.publish(channel, message_str)
    print(f"📤 Redis PUBLISH → {channel} : {message}")

    return {"status": "success", "channel": channel, "message": message_str}

# 채널에 전송 및 history 저장 및 유지
async def publish_with_save(channel: str, message: str, sender: str = "anonymous"):
    """
    1. Redis List에 메시지 저장
    2. Redis Pub/Sub로 실시간 전송
    """
    global redis_client

    # channel: chat:room1
    # history_key: chat_history:room1
    room_name = channel.replace("chat:", "", 1)
    history_key = f"chat_history:{room_name}"

    payload = {
        "sender": sender,
        "message": message,
        "channel": channel,
        "timestamp": datetime.utcnow().isoformat()
    }

    message_str = json.dumps(payload, ensure_ascii=False)

    # 1. 저장
    await redis_client.rpush(history_key, message_str)

    # 최근 100개만 유지
    await redis_client.ltrim(history_key, -100, -1)

    # 2. 실시간 전송
    await redis_client.publish(channel, message_str)

    print(f"💾 Redis SAVE -> {history_key} : {message_str}")
    print(f"📢 Redis PUBLISH -> {channel} : {message_str}")

#
async def get_chat_history(channel: str, start: int = 0, end: int = -1):
    """
    저장된 채팅 내역 조회
    """
    global redis_client

    room_name = channel.replace("chat:", "", 1)
    history_key = f"chat_history:{room_name}"
    
    messages  = await redis_client.lrange(history_key, start, end)
    return messages

# 3. Rate Limiting
async def redis_rate_limit(key: str, limit: int = 60, period: int = 60):
    """Rate Limiting (1분에 limit번)"""
    current = await redis_client.incr(key)
    if current == 1:
        await redis_client.expire(key, period)
    return current <= limit

# 4. 세션 관리 (로그인 세션)
async def redis_set_session(user_id: int, data: dict, expire: int = 86400):  # 24시간
    key = f"session:{user_id}"
    await set_value(key, data, expire)

async def redis_get_session(user_id: int):
    key = f"session:{user_id}"
    return await get_value(key)

# Pub/Sub 구독 Task
pubsub_task: asyncio.Task | None = None

# 당신이 만든 Pub/Sub 구독 함수 (그대로 유지)
async def subscribe_to_channel(channel: str = "chat:FastAPI_Chat"):
    pubsub = redis_client.pubsub()          # ← redis_client는 init_redis()에서 만들어진 것 사용
    await pubsub.subscribe(channel)
    print(f"📡 Redis Pub/Sub 구독 시작 → {channel}")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                print(f"📨 [Redis Pub/Sub] {channel} 수신: {message['data']}")
    except asyncio.CancelledError:
        print(f"🛑 {channel} 구독 Task가 취소되었습니다.")
        await pubsub.unsubscribe(channel)
        await pubsub.close()
    except Exception as e:
        print(f"❌ Pub/Sub 오류: {e}")

# lifespan에서 호출하기 편하도록 Helper 함수
async def start_pubsub_task(channel: str = "chat:FastAPI_Chat"):
    """Pub/Sub Task 시작 (lifespan에서 사용)"""
    global pubsub_task
    pubsub_task = asyncio.create_task(subscribe_to_channel(channel))
    print(f"📡 Pub/Sub Task 시작됨 → {channel}")

