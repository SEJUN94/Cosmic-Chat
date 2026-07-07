from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "My FastAPI Oracle Project"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    

    # Oracle DB 연결 정보 (.env에서 읽어옴)
    DATABASE_URL: str

    # Redis 설정 (.env에서 읽어옴)
    REDIS_URL: str
    REDIS_HOST : str
    REDIS_PORT : int
    HISTORY_LIMIT : int
    CHANNEL_PREFIX : str
    HISTORY_PREFIX : str

    # Kafka 설정(.env에서 읽어옴)
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TOPIC_ORDERS: str = "orders"      # 예시 토픽
    KAFKA_TOPIC_NOTIFICATIONS: str = "notifications"

    model_config = SettingsConfigDict(
        env_file=".env",              # 루트에 있는 .env 파일
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )

# 설정을 한 번만 로드하도록 캐싱 (성능 + 안정성)
@lru_cache()
def get_settings() -> Settings:
    settings = Settings()          # ← 원래 코드
    print("🔍 로드된 DATABASE_URL:", settings.DATABASE_URL)   # ← 이 줄 추가
    print("🔍 로드된 REDIS_URL:", settings.REDIS_URL)   # ← 이 줄 추가
    return settings