from fastapi import APIRouter
from app.core.kafka import send_to_kafka

router = APIRouter(prefix="/kafka", tags=["kafka"])

@router.post("/produce")
async def produce_message(topic: str = "test-topic", message: dict = {"hello": "kafka"}):
    await send_to_kafka(topic, message)
    return {"status": "sent", "topic": topic, "message": message}