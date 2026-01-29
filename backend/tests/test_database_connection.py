# Test Database Connection
# In Python REPL
import asyncio
from app.database import init_db, engine

async def test():
    await init_db()
    print(f"✅ Connected to: {engine.url}")

asyncio.run(test())