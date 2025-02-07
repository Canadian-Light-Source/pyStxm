from pymongo import MongoClient

# Replace with your MongoDB URI
uri = "mongodb://<mongo host ip addr here>:27017"

try:
    # Connect to the MongoDB server
    client = MongoClient(uri)

    # Access the server information
    server_info = client.server_info()  # Forces a connection attempt
    print("Connection successful:", server_info)

    # List databases
    print("Databases:", client.list_database_names())
except Exception as e:
    print("Connection failed:", e)