import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB = os.getenv("MONGO_DB", "gateway_logs")
    MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "logs")
    OPENAPI_URLS = [
        url.strip() for url in os.getenv("OPENAPI_URLS", "").split("||") if url.strip()
    ]

settings = Settings()