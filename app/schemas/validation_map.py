from pydantic import BaseModel
from datetime import date
from typing import Optional

class ValidationMapResponse(BaseModel):
    """조회용 DTO (Response)"""
    URI: str
    QUERY_ID: Optional[str] = None
    MAP_ID: int
    LAST_MDFY_DT: Optional[date] = None
    LAST_MDFR_ID: Optional[str] = None
    FRST_RGSR_DT: date
    FRST_REGST_ID: str
    DEL_YN: str

    model_config = {"from_attributes": True}   # SQLAlchemy 모델과 자동 매핑