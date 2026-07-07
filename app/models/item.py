from sqlalchemy import Column, Integer, String, Float
from app.core.database import Base

class Item(Base):
    __tablename__ = "ITEMS"   # Oracle은 대문자 추천

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    description = Column(String(200), nullable=True)