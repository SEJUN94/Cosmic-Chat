from pydantic import BaseModel, ConfigDict
from typing import Optional

# Request DTO (Create / Update)
class ItemCreate(BaseModel):
    name: str
    price: float
    description: Optional[str] = None

# Response DTO (조회용) - DB 모델과 필드가 달라도 OK
class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    description: Optional[str] = None

    # SQLAlchemy 모델에서 바로 변환할 수 있게 설정 (Java의 @JsonIgnore처럼)
    model_config = ConfigDict(from_attributes=True)