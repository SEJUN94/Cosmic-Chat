import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test():
    engine = create_async_engine(
        "oracle+oracledb://admn:admn!123@119.203.251.35:1521/orcl",
        echo=True
    )
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT '연결 성공!' FROM dual"))
        print(result.scalar())

asyncio.run(test())