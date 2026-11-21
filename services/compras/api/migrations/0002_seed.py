from django.db import migrations

SUPPLIERS = [
    ("900123456-7", "Agroquímicos del Café S.A.S.", "MULTINACIONAL", "ventas@agrocafe.co", 8),
    ("800987654-1", "Fertilizantes Andinos Ltda.", "IMPORTADOR", "pedidos@fertiandinos.co", 12),
]


def seed(apps, schema_editor):
    Supplier = apps.get_model("api", "Supplier")
    for nit, name, stype, email, lead_time in SUPPLIERS:
        Supplier.objects.get_or_create(nit=nit, defaults={"name": name, "type": stype, "email": email,
                                                          "default_lead_time_days": lead_time})


class Migration(migrations.Migration):
    dependencies = [("api", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
