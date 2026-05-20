from pymongo import MongoClient
from config.settings import settings

# Connect to MongoDB cluster
client = MongoClient(settings.MONGODB_URI)

# Explicitly select the database by name (DB_NAME from .env, fallback to "jobber")
db = client[settings.DB_NAME]

def get_db():
    """Dependency provider yielding our main database reference."""
    return db