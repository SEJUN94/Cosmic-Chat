from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings   # ← Pydantic Settings 사용

import os

settings = get_settings()


# PostgreSQL 예시 (나중에 Docker로 쉽게 띄울 수 있음)
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/fastapi_db"

# 세션 팩토리 (Spring의 EntityManager 같은 역할)
engine = create_async_engine(settings.DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Base 클래스 (Java의 @Entity 상속 역할)
class Base(DeclarativeBase):
    pass

# Dependency (Spring의 @Autowired Session 같은 역할)
# FastAPI Dependency (매 요청마다 DB 세션 생성)
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session