from datetime import datetime, timezone

from django.conf import settings
from pymongo import MongoClient

client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=2000)
db = client[settings.MONGO_DB]
_seeded = False

CATEGORIES = [
    {"_id": "cat-agroquimicos", "id": "cat-agroquimicos", "name": "Agroquímicos", "parentId": None},
    {"_id": "cat-fungicidas", "id": "cat-fungicidas", "name": "Fungicidas", "parentId": "cat-agroquimicos"},
    {"_id": "cat-fertilizantes", "id": "cat-fertilizantes", "name": "Fertilizantes", "parentId": None},
]
PRODUCTS = [
    {
        "_id": "p-agq-0153", "id": "p-agq-0153", "code": "AGQ-0153", "name": "Fungicida Alto 100 SL 1L",
        "type": "AGROQUIMICO", "categoryId": "cat-fungicidas", "unit": "LITRO", "referencePrice": 98500,
        "usualSupplierId": 1, "requiresLot": True, "icaRegistration": "ICA-1234",
        "technicalSheet": {"activeIngredient": "Ciproconazol", "toxicologicalCategory": "III"}, "active": True,
    },
    {
        "_id": "p-fer-0001", "id": "p-fer-0001", "code": "FER-0001", "name": "Urea 46% bulto 50 kg",
        "type": "FERTILIZANTE", "categoryId": "cat-fertilizantes", "unit": "BULTO", "referencePrice": 165000,
        "usualSupplierId": 2, "requiresLot": False, "icaRegistration": None, "technicalSheet": {}, "active": True,
    },
]


def collection(name):
    global _seeded
    if not _seeded:
        now = datetime.now(timezone.utc).isoformat()
        for c in CATEGORIES:
            db.categories.update_one({"_id": c["_id"]}, {"$setOnInsert": c}, upsert=True)
        for p in PRODUCTS:
            db.products.update_one({"_id": p["_id"]}, {"$setOnInsert": {**p, "createdAt": now, "updatedAt": now}},
                                   upsert=True)
        db.products.create_index("code", unique=True)
        _seeded = True
    return db[name]
