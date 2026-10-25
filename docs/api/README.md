# Contratos de API (OpenAPI 3.0)

| Servicio | Contrato | Stack | Puerto local |
|---|---|---|---|
| API Gateway | (enrutamiento, ver tabla abajo) | Laravel + MySQL | 8000 |
| Identidad | [identidad.json](identidad.json) | Django + MySQL | 8001 |
| Catálogo | [catalogo.json](catalogo.json) | Django + MongoDB | 8002 |
| Inventario | [inventario.json](inventario.json) | Django + MySQL | 8003 |
| Compras | [compras.json](compras.json) | Django + MySQL | 8004 |
| Reportes | [reportes.json](reportes.json) | Django + MongoDB | 8005 |

Visualizar: pegar el JSON en https://editor.swagger.io o usar la extensión "OpenAPI (Swagger) Editor" de VS Code.
Validar: `python -m pip install openapi-spec-validator` y `python -m openapi_spec_validator <archivo>.json`.

## Convenciones comunes

- Prefijo y versión: `/api/v1`.
- Autenticación: JWT `Authorization: Bearer <token>` emitido por Identidad. El Gateway valida firma y vigencia
  (sin llamar a Identidad) y consulta su lista de `jti` revocados (logout).
- Cabeceras internas que el Gateway reenvía a los servicios:
  - `X-User-Id`, `X-User-Role`, `X-User-Warehouses` (ids separados por coma; vacío = todas las bodegas).
  - `X-Correlation-Id` (lo genera el Gateway si no viene; se propaga en llamadas entre servicios).
- `Idempotency-Key` en escrituras reintentables (traslados, movimientos, recepciones). Mismo key = misma respuesta.
- Error estándar: `{ "code", "message", "details", "correlationId" }`.
- Paginación: `page` (desde 1), `size` (máx. 100); respuesta `{ page, size, total, items }`.
- `updatedSince` en listados que Reportes sondea cada 5 min (Catálogo, Inventario, Compras).
- `GET /health` en cada servicio (liveness/readiness de Kubernetes).
- `x-roles` en cada operación indica los roles permitidos: ADMIN, GERENTE, JEFE_COMPRAS, AUX_COMPRAS,
  JEFE_BODEGA, BODEGUERO, VENDEDOR, AUDITOR (`ALL` = cualquiera autenticado).
- Bajas lógicas (`active=false`) en productos, proveedores y usuarios.

## Enrutamiento del API Gateway

| Prefijo externo `/api/v1/...` | Servicio |
|---|---|
| `auth/*`, `users*`, `roles` | Identidad |
| `products*`, `categories*` | Catálogo |
| `warehouses*`, `stock*`, `fefo-suggestion`, `movements*`, `transfers*`, `min-stock`, `alerts/low-stock`, `customer-returns*`, `lots/*` | Inventario |
| `suppliers*`, `purchase-orders*`, `supplier-returns*`, `settings/approval-threshold` | Compras |
| `dashboard`, `reports/*`, `alerts/expiry`, `sync/*` | Reportes |
| `internal/*` | **Bloqueado** (solo tráfico entre servicios dentro del clúster) |

## Comunicación entre servicios (máx. 2 saltos en operaciones críticas)

- Despachar traslado: Gateway → Inventario.
- Recibir OC: Gateway → Compras → Inventario `POST /internal/entries` (`Idempotency-Key` = id de recepción).
- Devolver a proveedor: Gateway → Compras → Inventario `POST /internal/exits`.
- Crear OC: Compras → Catálogo `GET /products/{id}` (no crítica).
- Reportes → Catálogo/Inventario/Compras con `updatedSince` cada 5 min (fuera de la ruta crítica).
