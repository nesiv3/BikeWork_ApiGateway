from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import settings

client = AsyncIOMotorClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]
collection = db[settings.MONGO_COLLECTION]

async def log_request(data: dict):
    data["timestamp"] = datetime.now()
    await collection.insert_one(data)