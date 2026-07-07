from sqlalchemy import Column, Integer, String, Date, CHAR
from app.core.database import Base
from datetime import datetime

class TbSysValidationMap(Base):
    __tablename__ = "TB_SYS_VALIDATION_MAP"   # ← Oracle 테이블명 그대로 (대문자!)

    URI = Column(String(200), primary_key=True, nullable=False)          # 1
    QUERY_ID = Column(String(100), nullable=True)                        # 2
    MAP_ID = Column(Integer, nullable=False)                             # 3
    LAST_MDFY_DT = Column(Date, nullable=True)                          # 4
    LAST_MDFR_ID = Column(String(50), nullable=True)                     # 5
    FRST_RGSR_DT = Column(Date, nullable=False, default=datetime.now)    # 6
    FRST_REGST_ID = Column(String(50), nullable=False, default="SYSTEM") # 7
    DEL_YN = Column(CHAR(1), nullable=False, default="N")                # 8