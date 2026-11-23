import time

import requests
from locust import HttpUser, between, events, task

HOST = "http://127.0.0.1:8000/api/v1"
CLAVE = "Clave*2026"
USUARIOS = ("gerente", "jefe.compras", "jefe.bodega", "bodeguero.anserma", "vendedor.manizales")
TOKENS = {}


@events.test_start.add_listener
def obtener_tokens(environment, **kwargs):
    for usuario in USUARIOS:
        for _ in range(10):
            try:
                r = requests.post(f"{HOST}/auth/login", json={"username": usuario, "password": CLAVE}, timeout=30)
                if r.status_code == 200:
                    TOKENS[usuario] = r.json()["accessToken"]
                    break
            except requests.RequestException:
                pass
            time.sleep(3)


def token(usuario):
    return {"Authorization": f"Bearer {TOKENS.get(usuario, '')}"}


def check(client, method, path, expected, name, **kwargs):
    with client.request(method, path, name=name, catch_response=True, **kwargs) as response:
        if response.status_code == expected:
            response.success()
        else:
            response.failure(f"esperado {expected}, recibido {response.status_code}")


class Identidad(HttpUser):
    host = HOST
    wait_time = between(0.5, 1.5)

    @task
    def login_ok(self):
        check(self.client, "POST", "/auth/login", 200, "01 Identidad login OK [200]",
              json={"username": "admin", "password": CLAVE})

    @task
    def login_invalido(self):
        check(self.client, "POST", "/auth/login", 401, "02 Identidad login invalido [401]",
              json={"username": "admin", "password": "mala"})

    @task
    def usuarios_sin_admin(self):
        check(self.client, "GET", "/users", 403, "03 Identidad usuarios sin ADMIN [403]",
              headers=token("bodeguero.anserma"))


class Catalogo(HttpUser):
    host = HOST
    wait_time = between(0.5, 1.5)

    @task
    def buscar_productos(self):
        check(self.client, "GET", "/products?q=urea", 200, "04 Catalogo buscar productos [200]",
              headers=token("vendedor.manizales"))

    @task
    def producto_duplicado(self):
        check(self.client, "POST", "/products", 409, "05 Catalogo producto duplicado [409]",
              headers=token("jefe.compras"),
              json={"code": "AGQ-0153", "name": "Dup", "type": "AGROQUIMICO", "categoryId": "cat-fungicidas",
                    "unit": "LITRO", "referencePrice": 1, "requiresLot": True})

    @task
    def sin_token(self):
        check(self.client, "GET", "/products", 401, "06 Catalogo sin token [401]")


class Inventario(HttpUser):
    host = HOST
    wait_time = between(0.5, 1.5)

    @task
    def existencias(self):
        check(self.client, "GET", "/stock?warehouseId=CHI", 200, "07 Inventario existencias CHI [200]",
              headers=token("jefe.bodega"))

    @task
    def fefo(self):
        check(self.client, "GET", "/fefo-suggestion?productId=p-agq-0153&warehouseId=CHI&quantity=50", 200,
              "08 Inventario sugerencia FEFO [200]", headers=token("jefe.bodega"))

    @task
    def bodega_ajena(self):
        check(self.client, "POST", "/movements", 403, "09 Inventario bodega no asignada [403]",
              headers=token("bodeguero.anserma"),
              json={"type": "SALIDA", "productId": "p-fer-0001", "warehouseId": "CHI", "quantity": 1, "reason": "VENTA"})


class Compras(HttpUser):
    host = HOST
    wait_time = between(0.5, 1.5)

    @task
    def proveedores(self):
        check(self.client, "GET", "/suppliers", 200, "10 Compras listar proveedores [200]",
              headers=token("jefe.compras"))

    @task
    def nit_duplicado(self):
        check(self.client, "POST", "/suppliers", 409, "11 Compras NIT duplicado [409]",
              headers=token("jefe.compras"), json={"nit": "900123456-7", "name": "Duplicado"})

    @task
    def oc_producto_inexistente(self):
        check(self.client, "POST", "/purchase-orders", 422, "12 Compras OC producto inexistente [422]",
              headers=token("jefe.compras"),
              json={"supplierId": 1, "destinationWarehouseId": "CHI",
                    "lines": [{"productId": "no-existe", "quantity": 1, "unitPrice": 1}]})


class Reportes(HttpUser):
    host = HOST
    wait_time = between(0.5, 1.5)

    @task
    def dashboard(self):
        check(self.client, "GET", "/dashboard", 200, "13 Reportes dashboard [200]", headers=token("gerente"))

    @task
    def reporte_existencias(self):
        check(self.client, "GET", "/reports/stock", 200, "14 Reportes existencias consolidadas [200]",
              headers=token("gerente"))

    @task
    def dashboard_sin_permiso(self):
        check(self.client, "GET", "/dashboard", 403, "15 Reportes dashboard sin permiso [403]",
              headers=token("vendedor.manizales"))
