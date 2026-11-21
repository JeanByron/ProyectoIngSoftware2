from locust import HttpUser, between, task

GERENTE = {"X-User-Id": "2", "X-User-Role": "GERENTE", "X-Correlation-Id": "locust"}
JEFE_COMPRAS = {"X-User-Id": "3", "X-User-Role": "JEFE_COMPRAS", "X-Correlation-Id": "locust"}
JEFE_BODEGA = {"X-User-Id": "4", "X-User-Role": "JEFE_BODEGA", "X-User-Warehouses": "CHI,RSU", "X-Correlation-Id": "locust"}
BODEGUERO = {"X-User-Id": "5", "X-User-Role": "BODEGUERO", "X-User-Warehouses": "ANS", "X-Correlation-Id": "locust"}
VENDEDOR = {"X-User-Id": "6", "X-User-Role": "VENDEDOR", "X-User-Warehouses": "MZL", "X-Correlation-Id": "locust"}


def check(client, method, path, expected, name, **kwargs):
    with client.request(method, path, name=name, catch_response=True, **kwargs) as response:
        if response.status_code == expected:
            response.success()
        else:
            response.failure(f"esperado {expected}, recibido {response.status_code}")


class Identidad(HttpUser):
    host = "http://127.0.0.1:8001/api/v1"
    wait_time = between(0.5, 1.5)

    @task
    def login_ok(self):
        check(self.client, "POST", "/auth/login", 200, "01 Identidad login OK [200]",
              json={"username": "admin", "password": "Clave*2026"})

    @task
    def login_invalido(self):
        check(self.client, "POST", "/auth/login", 401, "02 Identidad login invalido [401]",
              json={"username": "admin", "password": "mala"})

    @task
    def usuarios_sin_admin(self):
        check(self.client, "GET", "/users", 403, "03 Identidad usuarios sin ADMIN [403]", headers=BODEGUERO)


class Catalogo(HttpUser):
    host = "http://127.0.0.1:8002/api/v1"
    wait_time = between(0.5, 1.5)

    @task
    def buscar_productos(self):
        check(self.client, "GET", "/products?q=urea", 200, "04 Catalogo buscar productos [200]", headers=VENDEDOR)

    @task
    def producto_duplicado(self):
        check(self.client, "POST", "/products", 409, "05 Catalogo producto duplicado [409]", headers=JEFE_COMPRAS,
              json={"code": "AGQ-0153", "name": "Dup", "type": "AGROQUIMICO", "categoryId": "cat-fungicidas",
                    "unit": "LITRO", "referencePrice": 1, "requiresLot": True})

    @task
    def sin_cabeceras(self):
        check(self.client, "GET", "/products", 401, "06 Catalogo sin cabeceras [401]")


class Inventario(HttpUser):
    host = "http://127.0.0.1:8003/api/v1"
    wait_time = between(0.5, 1.5)

    @task
    def existencias(self):
        check(self.client, "GET", "/stock?warehouseId=CHI", 200, "07 Inventario existencias CHI [200]", headers=JEFE_BODEGA)

    @task
    def fefo(self):
        check(self.client, "GET", "/fefo-suggestion?productId=p-agq-0153&warehouseId=CHI&quantity=50", 200,
              "08 Inventario sugerencia FEFO [200]", headers=JEFE_BODEGA)

    @task
    def bodega_ajena(self):
        check(self.client, "POST", "/movements", 403, "09 Inventario bodega no asignada [403]", headers=BODEGUERO,
              json={"type": "SALIDA", "productId": "p-fer-0001", "warehouseId": "CHI", "quantity": 1, "reason": "VENTA"})


class Compras(HttpUser):
    host = "http://127.0.0.1:8004/api/v1"
    wait_time = between(0.5, 1.5)

    @task
    def proveedores(self):
        check(self.client, "GET", "/suppliers", 200, "10 Compras listar proveedores [200]", headers=JEFE_COMPRAS)

    @task
    def nit_duplicado(self):
        check(self.client, "POST", "/suppliers", 409, "11 Compras NIT duplicado [409]", headers=JEFE_COMPRAS,
              json={"nit": "900123456-7", "name": "Duplicado"})

    @task
    def oc_producto_inexistente(self):
        check(self.client, "POST", "/purchase-orders", 422, "12 Compras OC producto inexistente [422]", headers=JEFE_COMPRAS,
              json={"supplierId": 1, "destinationWarehouseId": "CHI",
                    "lines": [{"productId": "no-existe", "quantity": 1, "unitPrice": 1}]})


class Reportes(HttpUser):
    host = "http://127.0.0.1:8005/api/v1"
    wait_time = between(0.5, 1.5)

    @task
    def dashboard(self):
        check(self.client, "GET", "/dashboard", 200, "13 Reportes dashboard [200]", headers=GERENTE)

    @task
    def reporte_existencias(self):
        check(self.client, "GET", "/reports/stock", 200, "14 Reportes existencias consolidadas [200]", headers=GERENTE)

    @task
    def dashboard_sin_permiso(self):
        check(self.client, "GET", "/dashboard", 403, "15 Reportes dashboard sin permiso [403]", headers=VENDEDOR)
