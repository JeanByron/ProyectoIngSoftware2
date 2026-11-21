from django.db import migrations

WAREHOUSES = [
    ("CHI", "Chinchiná", "CENTRAL"),
    ("MZL", "Manizales", "PUNTO_VENTA"),
    ("SRC", "Santa Rosa de Cabal", "PUNTO_VENTA"),
    ("ANS", "Anserma", "RURAL"),
    ("RSU", "Riosucio", "RURAL"),
]
PRODUCTS = [
    ("p-agq-0153", "AGQ-0153", "Fungicida Alto 100 SL 1L", "LITRO", True),
    ("p-fer-0001", "FER-0001", "Urea 46% bulto 50 kg", "BULTO", False),
]
STOCK = [
    ("p-agq-0153", "CHI", "L2026-031", "2027-01-15", 120),
    ("p-agq-0153", "CHI", "L2026-007", "2026-12-01", 40),
    ("p-fer-0001", "CHI", "", None, 600),
    ("p-fer-0001", "ANS", "", None, 5),
]


def seed(apps, schema_editor):
    Warehouse = apps.get_model("api", "Warehouse")
    ProductRef = apps.get_model("api", "ProductRef")
    Stock = apps.get_model("api", "Stock")
    for wid, name, wtype in WAREHOUSES:
        Warehouse.objects.get_or_create(id=wid, defaults={"name": name, "type": wtype})
    for pid, code, name, unit, requires_lot in PRODUCTS:
        ProductRef.objects.get_or_create(product_id=pid, defaults={"code": code, "name": name, "unit": unit,
                                                                   "requires_lot": requires_lot})
    for pid, wid, lot, expiry, qty in STOCK:
        Stock.objects.get_or_create(product_id=pid, warehouse_id=wid, lot_number=lot,
                                    defaults={"expiry_date": expiry, "quantity": qty})


class Migration(migrations.Migration):
    dependencies = [("api", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
