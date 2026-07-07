import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Depends          # ← Depends 추가!!!
from app.core.config import get_settings
from app.core.database import engine, Base, get_db   # get_db는 그대로
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.validation_map import TbSysValidationMap
from app.schemas.validation_map import ValidationMapResponse

#redis/kafka 필요 lib
from contextlib import asynccontextmanager
#route처리를 통해 inculde가 가능하여 redis관련 파일에 별도로 모아놓음 필요한 내용만 빼놓음
#from app.core.redis import init_redis, close_redis, subscribe_to_channel, set_value, get_value, delete_value, publish_message, publish_with_save, get_chat_history
from app.core.redis import init_redis, close_redis, subscribe_to_channel
from app.routers.redis_example import router as redis_router
import asyncio
#from app.core.kafka import start_kafka, stop_kafka   # 기존 Kafka 유지
from app.core.kafka import init_producer, close_producer
from app.routers.kafka import router as kafka_router
# redis chat app관련 함수 import
from app.routers.chat import router as chat_router
from app.routers.chat import init_chat_redis, close_chat_redis, redis_subscriber
from fastapi.staticfiles import StaticFiles

from fastapi.responses import RedirectResponse   # ← Redirect 사용을 위해 반드시 import 해야 합니다!

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Redis 초기화
    global redis_client
    await init_redis()           # Redis 연결
    await init_chat_redis()      # Chat App 연결
    #await create_topics()       # Kafka 토픽
    #await start_kafka()         # Kafka

    # Pub/Sub 백그라운드 Task 시작
    subscriber_task = asyncio.create_task(redis_subscriber())
    print("🚀 Realtime Chat App 시작")

    await init_producer()        # Kafka 시작할때
    yield
    await close_producer()       # Kafka 종료할때

    # ←←← Pub/Sub Task 시작 (여기에 추가!)
    global pubsub_task
    pubsub_task = asyncio.create_task(subscribe_to_channel("chat:FastAPI_Chat"))
    print("📡 Redis Pub/Sub 백그라운드 Task 시작 완료")
    
    print("🚀 FastAPI + Redis + Oracle 완전 시작!")
    yield
    
    # 종료 시 정리
    if subscriber_task is not None:
       subscriber_task.cancel()
       try:
           await subscriber_task
       except asyncio.CancelledError:
          pass
    await close_chat_redis()
    print("👋 채팅 애플리케이션 종료")

    # ===== Shutdown =====
    # Pub/Sub Task 안전하게 종료
    if pubsub_task:
        pubsub_task.cancel()
        try:
            await pubsub_task
        except asyncio.CancelledError:
            pass
        print("🛑 Pub/Sub Task 정상 종료")
    
    await close_redis()         # 기존 Redis 정리
    print("👋 FastAPI 서버 종료")
    #await stop_kafka()

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)
# Router 등록 
app.include_router(redis_router)
app.include_router(kafka_router)
app.include_router(chat_router)

#HTML 분리 코드
app.mount("/static", StaticFiles(directory="app/static"), name="static")



# GET / 요청이 오면 실행되는 함수
# Spring Boot의 @GetMapping("/")와 완전히 동일
@app.get("/")
def read_root():
    return {"message": "Hello World! Spring Boot에서 FastAPI로 오신 걸 환영합니다 🎉"}

@app.get("/redircect")
def read_root():
    # 외부 사이트로 리다이렉트
    return RedirectResponse(
        url="https://stg-ipt.tra.go.tz/ipt/react/index.html",   # ← 원하시는 전체 URL
        status_code=302   # 302: 임시 리다이렉트 (가장 일반적)
    )

# TB_SYS_VALIDATION_MAP 조회 테스트용 엔드포인트
@app.get("/validation-maps", response_model=list[ValidationMapResponse])
async def get_all_validation_maps(
    db: AsyncSession = Depends(get_db)                       # DB 세션 주입
):
    result = await db.execute(select(TbSysValidationMap))    # ← SQL 생성 + 실행
    items = result.scalars().all()                           # ← 결과 객체로 변환
    
    # 디버깅용 (터미널에 데이터 개수 출력)
    print(f"✅ 조회된 데이터 개수: {len(items)}개")
    if items:
        print("📋 첫 번째 데이터 예시:", vars(items[0]))
    
    return items

# 테이블 자동 생성은 Oracle 기존 테이블이 있어서 OFF
# @app.on_event("startup")
# async def startup():
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)

print(f"🚀 {settings.APP_NAME} started with Oracle DB!")