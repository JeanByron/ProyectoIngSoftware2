# Pruebas GET/POST con Thunder Client (localhost)

Los servicios de `services/` son **stubs de desarrollo**: implementan parte de los contratos de `docs/api/`
con datos en memoria (se reinician al detener el proceso). Las cabeceras `X-User-*` de cada petición simulan
lo que reenviará el API Gateway; por eso las pruebas van directo al puerto de cada servicio.

## 1. Instalar dependencias (una vez)

```bash
python -m pip install -r services/identidad/requirements.txt
```

## 2. Iniciar los servicios (todos Django; una terminal por servicio, desde la raíz del repo)

| Servicio | Comando | URL base |
|---|---|---|
| Identidad | `cd services/identidad && python manage.py runserver 127.0.0.1:8001` | http://127.0.0.1:8001/api/v1 |
| Catálogo | `cd services/catalogo && python manage.py runserver 127.0.0.1:8002` | http://127.0.0.1:8002/api/v1 |
| Inventario | `cd services/inventario && python manage.py runserver 127.0.0.1:8003` | http://127.0.0.1:8003/api/v1 |
| Compras | `cd services/compras && python manage.py runserver 127.0.0.1:8004` | http://127.0.0.1:8004/api/v1 |
| Reportes | `cd services/reportes && python manage.py runserver 127.0.0.1:8005` | http://127.0.0.1:8005/api/v1 |

Iniciar Reportes al final: sincroniza con Inventario al arrancar y luego cada 5 min (`POST /sync/run` fuerza).
Usar `127.0.0.1` y no `localhost`: en Windows `localhost` intenta primero IPv6 y añade ~2 s por petición.

## 3. Importar en Thunder Client

1. Thunder Client → Collections → menú `≡` → **Import** → `tests/thunder/agroinsumos.collection.json` (formato Postman).
2. Env → menú `≡` → **Import** → `tests/thunder/local.environment.json` y marcarlo como activo.
3. Ejecutar la colección en orden (Run All) con los servicios recién iniciados: las peticiones usan ids 1
   creados por las anteriores (OC 1, traslado 1).

El código HTTP esperado está en el nombre de cada petición (`[201]`, `[422]`…). Regenerar la colección:
`python tests/thunder/generar_coleccion.py`.

## Endpoints implementados en los stubs

Usuarios demo (contraseña `Clave*2026`): admin, gerente, jefe.compras, jefe.bodega, bodeguero.anserma, vendedor.manizales.

| Servicio | Método | Ruta | Qué prueba |
|---|---|---|---|
| Identidad | POST | `/auth/login` | Emite JWT; 401 credenciales, 400 datos |
| | GET | `/auth/me`, `/users`, `/users/{id}`, `/roles` | Consulta; 403 si no es ADMIN |
| | POST | `/users` | Alta; 409 duplicado |
| Catálogo | GET | `/products?q=&code=&categoryId=&supplierId=&type=` | Búsqueda y filtros (incluye subcategorías) |
| | GET | `/products/{id}`, `/categories?parentId=` | Consulta |
| | POST | `/products`, `/categories` | Alta; 409 duplicado; 403 sin rol |
| Inventario | GET | `/warehouses`, `/stock`, `/fefo-suggestion`, `/movements`, `/transfers/{id}` | Existencias, FEFO, kardex |
| | POST | `/movements` | ENTRADA/SALIDA (FEFO automático)/AJUSTE; 400 sin lote; 403 bodega ajena; 422 sin stock |
| | POST | `/transfers`, `/transfers/{id}/approve`, `/dispatch`, `/receive` | Flujo completo con diferencias; 409 estado inválido |
| | POST | `/internal/entries` | Entrada por recepción (solo Compras), idempotente |
| Compras | GET/POST | `/suppliers` | Directorio; 409 NIT duplicado |
| | POST | `/purchase-orders` | Crea OC consultando Catálogo; 422 producto inexistente |
| | POST | `/purchase-orders/{id}/approve`, `/send` | Estados; umbral → solo GERENTE |
| | POST | `/purchase-orders/{id}/receipts` | Recepción parcial → Inventario; 422 sin lote; reintento idempotente |
| Reportes | GET | `/dashboard`, `/reports/stock`, `/sync/status` | Copia sondeada con `freshness` |
| | POST | `/sync/run` | Fuerza sondeo |
| Todos | GET | `/health` | Health check |

Pendiente en los stubs (sí está en los contratos): logout/recuperación de contraseña, CRUD completo (PUT/DELETE),
devoluciones, stock mínimo/alertas, trazabilidad de lote, resto de reportes y el API Gateway en Laravel.
