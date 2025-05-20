from datetime import datetime
from pymongo import MongoClient
from core.config import settings

client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]
collection = db[settings.MONGO_COLLECTION]

def log_request(data: dict):
    data["timestamp"] = datetime.now()
    collection.insert_one(data)