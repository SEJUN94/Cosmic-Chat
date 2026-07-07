from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from app.core.config import get_settings
import json
import asyncio

settings = get_settings()

producer: AIOKafkaProducer | None = None

async def init_producer():
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8')
    )
    await producer.start()
    print("✅ Kafka Producer 시작됨")

async def close_producer():
    global producer
    if producer:
        await producer.stop()
        print("🛑 Kafka Producer 종료됨")

async def send_to_kafka(topic: str, message: dict):
    if producer is None:
        raise RuntimeError("Kafka Producer가 초기화되지 않았습니다.")
    await producer.send_and_wait(topic, message)
    print(f"📤 Kafka → {topic} : {message}")