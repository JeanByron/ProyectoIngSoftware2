"""Pruebas de rendimiento de Sebastián: sistema completo a través del API Gateway."""
import time

import requests
from locust import HttpUser, between, constant_pacing, events, tag, task

CLAVE = "Clave*2026"
TOKENS = {}  # un token por usuario de prueba, obtenido una vez antes de la prueba


def verificar(response, esperado):
    """Marca la petición como fallida si no devuelve el código esperado."""
    if response.status_code == esperado:
        response.success()
    else:
        response.failure(f"esperado {esperado}, recibido {response.status_code}")

@events.test_start.add_listener
def obtener_tokens(environment, **kwargs):
    """Se ejecuta una vez antes de la prueba: un login por rol, sin concurrencia."""
    for usuario in ("jefe.bodega", "gerente"):
        for _ in range(10):
            try:
                r = requests.post(f"{environment.host}/auth/login",
                                  json={"username": usuario, "password": CLAVE}, timeout=30)
                if r.status_code == 200:
                    TOKENS[usuario] = r.json()["accessToken"]
                    print(f"Token obtenido para {usuario}")
                    break
                print(f"Login de {usuario} respondió {r.status_code}, reintentando...")
            except requests.RequestException as error:
                print(f"Login de {usuario} falló ({error}), reintentando...")
            time.sleep(3)


def cabeceras(usuario):
    return {"Authorization": f"Bearer {TOKENS.get(usuario, '')}"}

class UsuarioBodega(HttpUser):
    """Jefe de bodega de Chinchiná: consulta existencias, FEFO y catálogo."""
    wait_time = between(1, 2)

    def on_start(self):
        self.headers = cabeceras("jefe.bodega")

    @tag("login")
    @task
    def login(self):
        with self.client.post("/auth/login", json={"username": "jefe.bodega", "password": CLAVE},
                              name="Login", catch_response=True) as r:
            verificar(r, 200)

    @tag("productos", "mixto")
    @task(2)
    def listar_productos(self):
        with self.client.get("/products", headers=self.headers, name="Listar productos",
                             catch_response=True) as r:
            verificar(r, 200)

    @tag("busqueda", "mixto")
    @task(1)
    def buscar_productos(self):
        with self.client.get("/products?q=urea", headers=self.headers, name="Buscar productos",
                             catch_response=True) as r:
            verificar(r, 200)

    @tag("stock", "mixto")
    @task(4)
    def existencias(self):
        with self.client.get("/stock?warehouseId=CHI", headers=self.headers, name="Existencias CHI",
                             catch_response=True) as r:
            verificar(r, 200)

    @tag("fefo", "mixto")
    @task(3)
    def sugerencia_fefo(self):
        with self.client.get("/fefo-suggestion?productId=p-agq-0153&warehouseId=CHI&quantity=50",
                             headers=self.headers, name="Sugerencia FEFO", catch_response=True) as r:
            verificar(r, 200)


class UsuarioGerente(HttpUser):
    """Gerente: consulta el dashboard."""
    wait_time = between(1, 2)

    def on_start(self):
        self.headers = cabeceras("gerente")

    @tag("dashboard")
    @task
    def dashboard(self):
        with self.client.get("/dashboard", headers=self.headers, name="Dashboard",
                             catch_response=True) as r:
            verificar(r, 200)


class UsuarioSinToken(HttpUser):
    """Cliente sin token: mide solo al Gateway, que rechaza sin llamar a ningún servicio."""
    wait_time = between(0.5, 1)

    @tag("sintoken")
    @task
    def sin_token(self):
        with self.client.get("/products", name="Rechazo sin token", catch_response=True) as r:
            verificar(r, 401)

class UsuarioLogin(HttpUser):
    """Empleado que inicia sesión una vez por minuto: ritmo realista para la carga normal (P01)."""
    wait_time = constant_pacing(60)

    @tag("login")
    @task
    def login(self):
        with self.client.post("/auth/login", json={"username": "jefe.bodega", "password": CLAVE},
                              name="Login", catch_response=True) as r:
            verificar(r, 200)