from django.contrib.auth.hashers import make_password
from django.db import migrations

USERS = [
    ("admin", "Administrador", "ADMIN", []),
    ("gerente", "Gerente General", "GERENTE", []),
    ("jefe.compras", "Jefe de Compras", "JEFE_COMPRAS", []),
    ("jefe.bodega", "Jefe Bodega Central", "JEFE_BODEGA", ["CHI"]),
    ("bodeguero.anserma", "Carlos Gómez", "BODEGUERO", ["ANS"]),
    ("vendedor.manizales", "Laura Ríos", "VENDEDOR", ["MZL"]),
]


def seed(apps, schema_editor):
    Usuario = apps.get_model("api", "Usuario")
    password = make_password("Clave*2026")
    for username, full_name, role, warehouses in USERS:
        Usuario.objects.get_or_create(
            username=username,
            defaults={"full_name": full_name, "email": f"{username}@agroinsumos.co", "role": role,
                      "warehouse_ids": warehouses, "password": password},
        )


class Migration(migrations.Migration):
    dependencies = [("api", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
