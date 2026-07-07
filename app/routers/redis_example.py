from fastapi import APIRouter, HTTPException, Depends
from app.core.redis import set_value, get_value, delete_value, publish_with_save, get_chat_history, redis_rate_limit, redis_set_session, redis_get_session

#from app.core.redis import (
#    redis_set, redis_get, redis_delete,
#    redis_publish, redis_rate_limit,
#    redis_set_session, redis_get_session
#)
#from app.core.dependencies import get_current_user   # JWT 인증이 있으면
#from app.schemas.auth import TokenData
import asyncio

router = APIRouter(prefix="/redis", tags=["Redis Examples"])

# ====================== 1. 캐싱 ======================
@router.post("/cache")
async def cache_example(data: dict):
    await redis_set("cache:user:1001", data, expire=300)   # 5분 캐싱
    return {"status": "cached", "key": "cache:user:1001"}

@router.get("/cache/{user_id}")
async def get_cache(user_id: int):
    data = await redis_get(f"cache:user:{user_id}")
    if data is None:
        return {"message": "캐시 미스 - DB에서 조회하세요"}
    return data

# ====================== 2. Pub/Sub ======================
#@router.post("/publish")
async def publish_message(message: dict):
    await redis_publish("chat:room1", message)
    return {"status": "published", "channel": "chat:room1"}

# ====================== 3. Rate Limiting ======================
@router.get("/rate-limit")
async def rate_limit_test():
    key = "rate:api:192.168.1.100"
    if not await redis_rate_limit(key, limit=10, period=60):
        raise HTTPException(status_code=429, detail="Too Many Requests")
    return {"message": "요청 허용"}

# ====================== 4. 세션 관리 ======================
@router.post("/session/{user_id}")
async def save_session(user_id: int, session_data: dict):
    await redis_set_session(user_id, session_data, expire=86400)
    return {"status": "session saved"}

@router.get("/session/{user_id}")
async def get_session(user_id: int):
    session = await redis_get_session(user_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션이 없습니다")
    return session

# ==================== Redis 테스트 API ====================

@router.post("/set")
async def redis_set(key: str, value: str, expire: int = 100000):
#async def redis_set(key: str, value: str):
    """Redis에 값 저장"""
    await set_value(key, value, expire)
    return {"status": "success", "key": key, "value": value, "expire": expire}
    #await set_value(key, value)
    #return {"status": "success", "key": key, "value": value}

@router.get("/get/{key}")
async def redis_get(key: str):
    """Redis에서 값 조회"""
    value = await get_value(key)
    return {"key": key, "value": value}


@router.delete("/delete/{key}")
async def redis_delete(key: str):
    """Redis에서 값 삭제"""
    success = await delete_value(key)
    return {"key": key, "deleted": success}


@router.post("/publish")
#async def redis_publish(channel: str = "chat:FastAPI_Chat", message: str = "테스트 메시지"):
async def redis_publish(channel: str = "chat:FastAPI_Chat", message: str = "테스트 메시지",sender: str = "anonymous"):
    """Pub/Sub로 메시지 발행"""
    #await publish_message(channel, message)
    #return {"status": "published", "channel": channel, "message": message}
    await publish_with_save(channel, message, sender)
    return {
        "success": True,
        "channel": channel,
        "message": message,
        "sender": sender
    }

@router.get("/history")
async def redis_history(channel: str = "chat:FastAPI_Chat", start: int = 0, end: int = -1):
    messages = await get_chat_history(channel, start, end)
    return {
        "channel": channel,
        "history_count": len(messages),
        "messages": messages
    }