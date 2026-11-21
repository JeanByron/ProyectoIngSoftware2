from django.conf import settings
from pymongo import MongoClient

client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=2000)
db = client[settings.MONGO_DB]
