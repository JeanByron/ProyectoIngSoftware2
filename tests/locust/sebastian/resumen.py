"""Genera resultados/RESUMEN.md con una tabla de las 15 pruebas a partir de los CSV de Locust."""
import csv
from pathlib import Path

PRUEBAS = {
    "P01": ("Login", "Normal", 25, 180),
    "P02": ("Listar productos", "Normal", 25, 120),
    "P03": ("Buscar productos", "Normal", 25, 120),
    "P04": ("Existencias", "Normal", 25, 120),
    "P05": ("Sugerencia FEFO", "Normal", 25, 120),
    "P06": ("Existencias", "Pico", 50, 180),
    "P07": ("Sugerencia FEFO", "Pico", 50, 180),
    "P08": ("Dashboard", "Pico", 50, 180),
    "P09": ("Uso mixto", "Pico", 50, 180),
    "P10": ("Rechazo sin token", "Pico", 50, 120),
    "P11": ("Existencias", "Estrés", 100, 240),
    "P12": ("Login", "Estrés", 100, 240),
    "P13": ("Uso mixto", "Estrés", 150, 240),
    "P14": ("Rechazo sin token", "Estrés", 200, 180),
    "P15": ("Uso mixto con Catálogo caído", "Resiliencia", 50, 240),
}
LIMITE_MS = 2000  # RNF06: consultas en menos de 2 s

carpeta = Path(__file__).parent / "resultados"
filas = ["| Prueba | Qué mide | Nivel | Usuarios | Peticiones | Fallos | Mediana | p95 | Peticiones/s | ¿p95 < 2 s? |",
         "|---|---|---|---|---|---|---|---|---|---|"]

for id_, (que, nivel, usuarios, segundos) in PRUEBAS.items():
    archivo = carpeta / id_ / f"{id_}_stats.csv"
    if not archivo.exists():
        filas.append(f"| {id_} | {que} | {nivel} | {usuarios} | pendiente | | | | | |")
        continue
    with archivo.open(newline="") as f:
        total = next(r for r in csv.DictReader(f) if r["Name"] == "Aggregated")
    peticiones = int(total["Request Count"])
    fallos = int(total["Failure Count"])
    porcentaje = 100 * fallos / peticiones if peticiones else 0
    p95 = float(total["95%"])
    cumple = "✅" if p95 < LIMITE_MS and porcentaje < 1 else "❌"
    filas.append(f"| [{id_}]({id_}/{id_}.html) | {que} | {nivel} | {usuarios} | {peticiones} | "
                 f"{porcentaje:.1f} % | {float(total['Median Response Time']):.0f} ms | {p95:.0f} ms | "
                 f"{peticiones / segundos:.1f} | {cumple} |")

(carpeta / "RESUMEN.md").write_text("# Resultados de las pruebas de rendimiento (Sebastián)\n\n"
                                     + "\n".join(filas) + "\n", encoding="utf-8")
print("\n".join(filas))