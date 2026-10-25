"""Genera la colección (formato Postman v2.1, importable en Thunder Client) y el environment local.
Uso: python generar_coleccion.py"""
import json
from pathlib import Path

OUT = Path(__file__).parent


def h(uid, role, warehouses=None):
    """Cabeceras que el API Gateway reenvía tras validar el JWT."""
    headers = [{"key": "X-User-Id", "value": str(uid)}, {"key": "X-User-Role", "value": role}]
    if warehouses:
        headers.append({"key": "X-User-Warehouses", "value": warehouses})
    return headers


ADMIN, GER, JC = h(1, "ADMIN"), h(2, "GERENTE"), h(3, "JEFE_COMPRAS")
JB, BOD, VEN = h(4, "JEFE_BODEGA", "CHI,RSU"), h(5, "BODEGUERO", "ANS"), h(6, "VENDEDOR", "MZL")


def ik(key):
    return [{"key": "Idempotency-Key", "value": key}]


def req(name, method, svc, path, headers=(), body=None, expect=200, extra=()):
    hdrs = list(headers) + list(extra)
    if body is not None:
        hdrs.append({"key": "Content-Type", "value": "application/json"})
    item = {"name": f"{name} [{expect}]",
            "request": {"method": method, "header": hdrs, "url": {"raw": "{{" + svc + "}}" + path},
                        "description": f"Esperado: HTTP {expect}"}}
    if body is not None:
        item["request"]["body"] = {"mode": "raw", "raw": json.dumps(body, ensure_ascii=False, indent=2)}
    return item


RECEPCION = {"deliveryNote": "REM-8812",
             "lines": [{"lineId": 1, "quantity": 60, "lotNumber": "L2026-090", "expiryDate": "2027-06-30"}]}

FOLDERS = {
    "1 Identidad": [
        req("Health", "GET", "identidad", "/health"),
        req("Login OK", "POST", "identidad", "/auth/login", body={"username": "admin", "password": "Clave*2026"}),
        req("Login credenciales inválidas", "POST", "identidad", "/auth/login",
            body={"username": "admin", "password": "mala"}, expect=401),
        req("Login sin password", "POST", "identidad", "/auth/login", body={"username": "admin"}, expect=400),
        req("Usuario autenticado (me)", "GET", "identidad", "/auth/me", ADMIN),
        req("Listar usuarios por rol", "GET", "identidad", "/users?role=BODEGUERO", ADMIN),
        req("Crear usuario", "POST", "identidad", "/users", ADMIN,
            {"username": "bodeguero.riosucio", "fullName": "Ana Torres", "email": "ana@agroinsumos.co",
             "role": "BODEGUERO", "warehouseIds": ["RSU"], "password": "Clave*2026"}, 201),
        req("Crear usuario duplicado", "POST", "identidad", "/users", ADMIN,
            {"username": "admin", "fullName": "X", "email": "x@x.co", "role": "ADMIN", "password": "Clave*2026"}, 409),
        req("Listar usuarios sin rol ADMIN", "GET", "identidad", "/users", BOD, expect=403),
    ],
    "2 Catalogo": [
        req("Health", "GET", "catalogo", "/health"),
        req("Buscar productos por nombre", "GET", "catalogo", "/products?q=urea", VEN),
        req("Filtrar por categoría (incluye subcategorías)", "GET", "catalogo",
            "/products?categoryId=cat-agroquimicos", VEN),
        req("Filtrar por proveedor habitual", "GET", "catalogo", "/products?supplierId=2", VEN),
        req("Consultar producto", "GET", "catalogo", "/products/p-agq-0153", VEN),
        req("Crear producto (semilla)", "POST", "catalogo", "/products", JC,
            {"code": "SEM-0010", "name": "Semilla café Castillo 1 kg", "type": "SEMILLA",
             "categoryId": "cat-fertilizantes", "unit": "KILO", "referencePrice": 45000, "usualSupplierId": 1,
             "requiresLot": True, "technicalSheet": {"variety": "Castillo", "germinationPct": 85}}, 201),
        req("Crear producto código duplicado", "POST", "catalogo", "/products", JC,
            {"code": "AGQ-0153", "name": "Dup", "type": "AGROQUIMICO", "categoryId": "cat-fungicidas",
             "unit": "LITRO", "referencePrice": 1, "requiresLot": True}, 409),
        req("Crear producto sin permiso (vendedor)", "POST", "catalogo", "/products", VEN, {"code": "X"}, 403),
        req("Listar categorías raíz", "GET", "catalogo", "/categories", VEN),
        req("Crear subcategoría", "POST", "catalogo", "/categories", JC,
            {"name": "Insecticidas", "parentId": "cat-agroquimicos"}, 201),
        req("Sin cabeceras del Gateway", "GET", "catalogo", "/products", expect=401),
    ],
    "3 Inventario": [
        req("Health", "GET", "inventario", "/health"),
        req("Listar bodegas", "GET", "inventario", "/warehouses", VEN),
        req("Existencias en Chinchiná", "GET", "inventario", "/stock?warehouseId=CHI", JB),
        req("Sugerencia FEFO", "GET", "inventario",
            "/fefo-suggestion?productId=p-agq-0153&warehouseId=CHI&quantity=50", JB),
        req("FEFO stock insuficiente", "GET", "inventario",
            "/fefo-suggestion?productId=p-agq-0153&warehouseId=CHI&quantity=99999", JB, expect=422),
        req("Salida por venta con FEFO automático", "POST", "inventario", "/movements", JB,
            {"type": "SALIDA", "productId": "p-agq-0153", "warehouseId": "CHI", "quantity": 5, "reason": "VENTA"},
            201, ik("mov-001")),
        req("Entrada sin lote en producto con lote", "POST", "inventario", "/movements", JB,
            {"type": "ENTRADA", "productId": "p-agq-0153", "warehouseId": "CHI", "quantity": 10,
             "reason": "CARGA_INICIAL"}, 400),
        req("Movimiento en bodega no asignada", "POST", "inventario", "/movements", BOD,
            {"type": "SALIDA", "productId": "p-fer-0001", "warehouseId": "CHI", "quantity": 1, "reason": "VENTA"},
            403),
        req("Kardex del producto", "GET", "inventario", "/movements?productId=p-agq-0153", JB),
        req("Solicitar traslado CHI→RSU", "POST", "inventario", "/transfers", VEN,
            {"originId": "CHI", "destinationId": "RSU", "items": [{"productId": "p-agq-0153", "quantity": 30}]},
            201, ik("tr-001")),
        req("Despachar sin aprobar", "POST", "inventario", "/transfers/1/dispatch", JB, expect=409),
        req("Aprobar traslado", "POST", "inventario", "/transfers/1/approve", JB),
        req("Despachar traslado (descuenta origen)", "POST", "inventario", "/transfers/1/dispatch", JB,
            extra=ik("tr-001-dispatch")),
        req("Recibir con diferencia", "POST", "inventario", "/transfers/1/receive", JB,
            {"lots": [{"productId": "p-agq-0153", "lotNumber": "L2026-031", "receivedQuantity": 13,
                       "differenceReason": "Envase roto"}]}, 200, ik("tr-001-receive")),
        req("Consultar traslado", "GET", "inventario", "/transfers/1", GER),
    ],
    "4 Compras": [
        req("Health", "GET", "compras", "/health"),
        req("Listar proveedores", "GET", "compras", "/suppliers", JC),
        req("Registrar proveedor", "POST", "compras", "/suppliers", JC,
            {"nit": "901555222-3", "name": "Herramientas del Eje S.A.S.", "type": "FABRICANTE_NACIONAL",
             "defaultLeadTimeDays": 5}, 201),
        req("Crear OC (consulta Catálogo)", "POST", "compras", "/purchase-orders", JC,
            {"supplierId": 1, "destinationWarehouseId": "CHI", "expectedDeliveryDate": "2026-11-05",
             "lines": [{"productId": "p-agq-0153", "quantity": 100, "unitPrice": 95000}]}, 201),
        req("Crear OC producto inexistente", "POST", "compras", "/purchase-orders", JC,
            {"supplierId": 1, "destinationWarehouseId": "CHI",
             "lines": [{"productId": "no-existe", "quantity": 1, "unitPrice": 1}]}, 422),
        req("Aprobar OC", "POST", "compras", "/purchase-orders/1/approve", JC),
        req("Enviar OC al proveedor", "POST", "compras", "/purchase-orders/1/send", JC),
        req("Recepción sin lote", "POST", "compras", "/purchase-orders/1/receipts", JB,
            {"lines": [{"lineId": 1, "quantity": 60}]}, 422, ik("rec-000")),
        req("Recepción parcial (entrada en Inventario)", "POST", "compras", "/purchase-orders/1/receipts", JB,
            RECEPCION, 201, ik("rec-001")),
        req("Reintento misma Idempotency-Key (no duplica)", "POST", "compras", "/purchase-orders/1/receipts", JB,
            RECEPCION, 201, ik("rec-001")),
        req("Consultar OC (RECIBIDA_PARCIAL)", "GET", "compras", "/purchase-orders/1", JC),
    ],
    "5 Reportes": [
        req("Health", "GET", "reportes", "/health"),
        req("Forzar sincronización", "POST", "reportes", "/sync/run", ADMIN, expect=202),
        req("Estado de sincronización", "GET", "reportes", "/sync/status", GER),
        req("Dashboard", "GET", "reportes", "/dashboard", GER),
        req("Reporte de existencias consolidadas", "GET", "reportes", "/reports/stock", GER),
        req("Dashboard sin permiso (vendedor)", "GET", "reportes", "/dashboard", VEN, expect=403),
    ],
}

PORTS = {"identidad": 8001, "catalogo": 8002, "inventario": 8003, "compras": 8004, "reportes": 8005}

if __name__ == "__main__":
    collection = {
        "info": {"name": "AgroInsumos - Microservicios (localhost)",
                 "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                 "description": "Pruebas GET/POST por servicio. X-User-* simula lo que reenvía el API Gateway. "
                                "Ejecutar en orden con los servicios recién iniciados."},
        "item": [{"name": name, "item": items} for name, items in FOLDERS.items()],
    }
    environment = {"name": "local", "values": [
        {"key": k, "value": f"http://127.0.0.1:{p}/api/v1", "enabled": True} for k, p in PORTS.items()]}
    (OUT / "agroinsumos.collection.json").write_text(json.dumps(collection, ensure_ascii=False, indent=2), "utf8")
    (OUT / "local.environment.json").write_text(json.dumps(environment, indent=2), "utf8")
    print(sum(len(v) for v in FOLDERS.values()), "requests")
