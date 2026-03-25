from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import certifi

# Use your new credentials
uri = "mongodb+srv://smart_pantry_user:SmartPantry123@vamshikrishna.ofso7db.mongodb.net/?retryWrites=true&w=majority"

print(f"Testing connection with new user...")
print(f"Connection string: {uri.replace('SmartPantry123', '****')}")

try:
    client = MongoClient(uri, server_api=ServerApi('1'), tlsCAFile=certifi.where())
    client.admin.command('ping')
    print("✅ SUCCESS! Connected to MongoDB Atlas!")
    
    # List databases
    dbs = client.list_database_names()
    print(f"Available databases: {dbs}")
    
except Exception as e:
    print(f"❌ FAILED: {e}")