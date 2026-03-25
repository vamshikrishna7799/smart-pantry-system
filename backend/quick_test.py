from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import certifi

# Your connection string with password
uri = "mongodb+srv://smartpantryuser:SmartPantry123@vamshikrishna.ofso7db.mongodb.net/?retryWrites=true&w=majority"

print("Attempting to connect to MongoDB...")
print(f"Connection string: {uri.replace('cdb_password', '****')}")

try:
    # Create client with proper TLS settings
    client = MongoClient(uri, server_api=ServerApi('1'), tlsCAFile=certifi.where())
    
    # Send a ping to confirm connection
    client.admin.command('ping')
    print("✅ SUCCESS! Connected to MongoDB Atlas!")
    
    # List databases
    dbs = client.list_database_names()
    print(f"Available databases: {dbs}")
    
except Exception as e:
    print(f"❌ FAILED: {e}")