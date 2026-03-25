# database.py
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from config import Config
import certifi

# MongoDB Connection
client = MongoClient(Config.MONGO_URI, server_api=ServerApi('1'), tlsCAFile=certifi.where())
db = client[Config.MONGO_DB_NAME]

# Collections
users_collection = db['users']
pantry_items_collection = db['pantry_items']
profiles_collection = db['profiles']
otp_collection = db['otp_requests']

# Create indexes
def create_indexes():
    try:
        users_collection.create_index('email', unique=True)
        users_collection.create_index('username', unique=True)
        pantry_items_collection.create_index([('user_id', 1), ('profile_id', 1), ('name', 1)])
        pantry_items_collection.create_index('expiry_date')
        profiles_collection.create_index([('user_id', 1), ('profile_name', 1)], unique=True)
        print("✅ Database indexes created successfully!")
    except Exception as e:
        print(f"⚠️ Index creation warning: {e}")

create_indexes()