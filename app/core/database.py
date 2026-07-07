from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

# Oracle 연결 (oracledb 드라이버 사용)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,           # True면 SQL 로그 출력
    future=True
)

# 세션 생성기
AsyncSessionLocal = async_sessionmaker(
    engine, 
    expire_on_commit=False,
    autoflush=False
)

# 모든 모델이 상속받을 Base 클래스
class Base(DeclarativeBase):
    pass

# FastAPI에서 DB 세션 주입용 Dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session