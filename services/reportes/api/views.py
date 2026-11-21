import json
import os
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from pymongo.errors import PyMongoError

from .common import roles
from .db import db

INVENTARIO_URL = os.getenv("INVENTARIO_URL", "http://127.0.0.1:8003/api/v1")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "300"))
SERVICE_HEADERS = {"X-User-Id": "0", "X-User-Role": "AUDITOR"}
NO_ID = {"_id": 0}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _sources():
    saved = db.sources.find_one({"_id": "inventario"}, NO_ID) or {}
    return [{"source": "inventario", "lastSyncAt": None, "stale": True, "lastError": "Sin sincronizar", **saved}]


def sync():
    try:
        req = urllib.request.Request(f"{INVENTARIO_URL}/stock?size=100", headers=SERVICE_HEADERS)
        with urllib.request.urlopen(req, timeout=2) as resp:
            items = json.loads(resp.read())["items"]
        db.stock.delete_many({})
        if items:
            db.stock.insert_many(items)
        db.sources.update_one({"_id": "inventario"},
                              {"$set": {"lastSyncAt": _now(), "stale": False, "lastError": None}}, upsert=True)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        db.sources.update_one({"_id": "inventario"}, {"$set": {"stale": True, "lastError": str(exc)}}, upsert=True)
    except PyMongoError:
        pass


def start_scheduler():
    sync()
    timer = threading.Timer(POLL_SECONDS, start_scheduler)
    timer.daemon = True
    timer.start()


def _freshness():
    return {"generatedAt": _now(), "sources": _sources()}


@require_http_methods(["GET"])
@roles("GERENTE", "JEFE_COMPRAS", "AUX_COMPRAS", "JEFE_BODEGA", "AUDITOR")
def dashboard(request):
    warehouse = request.GET.get("warehouseId")
    query = {"warehouseId": warehouse} if warehouse is not None else {}
    rows = list(db.stock.find(query, NO_ID))
    by_wh = {}
    for r in rows:
        by_wh[r["warehouseId"]] = by_wh.get(r["warehouseId"], 0) + r["quantity"]
    return JsonResponse({
        "freshness": _freshness(),
        "unitsByWarehouse": [{"warehouseId": w, "units": q} for w, q in sorted(by_wh.items())],
        "stockOutCount": sum(1 for r in rows if r["quantity"] <= 0),
        "lotsTracked": sum(1 for r in rows if r["lotNumber"]),
        "note": "Stub: valorización, rotación y OC pendientes se calcularán al sincronizar Catálogo y Compras",
    })


@require_http_methods(["GET"])
@roles("GERENTE", "JEFE_COMPRAS", "AUX_COMPRAS", "JEFE_BODEGA", "AUDITOR")
def stock_report(request):
    report = {}
    for r in db.stock.find({}, NO_ID):
        p = r["product"] or {}
        item = report.setdefault(p.get("productId"), {"productId": p.get("productId"), "code": p.get("code"),
                                                        "name": p.get("name"), "byWarehouse": {}, "total": 0})
        item["byWarehouse"][r["warehouseId"]] = item["byWarehouse"].get(r["warehouseId"], 0) + r["quantity"]
        item["total"] += r["quantity"]
    return JsonResponse({"freshness": _freshness(), "items": list(report.values())})


@require_http_methods(["GET"])
@roles("ADMIN", "GERENTE")
def sync_status(request):
    return JsonResponse(_sources(), safe=False)


@csrf_exempt
@require_http_methods(["POST"])
@roles("ADMIN")
def sync_run(request):
    threading.Thread(target=sync, daemon=True).start()
    return JsonResponse({"message": "Sincronización encolada"}, status=202)
