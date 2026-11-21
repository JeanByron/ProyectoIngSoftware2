import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Movement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(max_length=20)),
                ('product_id', models.CharField(max_length=64)),
                ('warehouse_id', models.CharField(max_length=10)),
                ('lot_number', models.CharField(max_length=64, null=True)),
                ('quantity', models.FloatField()),
                ('balance_after', models.FloatField()),
                ('reason', models.CharField(max_length=255)),
                ('reference_type', models.CharField(max_length=30, null=True)),
                ('reference_id', models.CharField(max_length=64, null=True)),
                ('user_id', models.BigIntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'movements',
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='ProductRef',
            fields=[
                ('product_id', models.CharField(max_length=64, primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=50)),
                ('name', models.CharField(max_length=200)),
                ('unit', models.CharField(max_length=20)),
                ('requires_lot', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'product_refs',
            },
        ),
        migrations.CreateModel(
            name='Warehouse',
            fields=[
                ('id', models.CharField(max_length=10, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('type', models.CharField(max_length=20)),
                ('active', models.BooleanField(default=True)),
            ],
            options={
                'db_table': 'warehouses',
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='IdempotencyRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', models.CharField(max_length=255)),
                ('key', models.CharField(max_length=255)),
                ('status', models.IntegerField()),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'idempotency_records',
                'unique_together': {('path', 'key')},
            },
        ),
        migrations.CreateModel(
            name='Transfer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(max_length=30)),
                ('items', models.JSONField(default=list)),
                ('history', models.JSONField(default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('destination', models.ForeignKey(db_column='destination_id', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='api.warehouse')),
                ('origin', models.ForeignKey(db_column='origin_id', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='api.warehouse')),
            ],
            options={
                'db_table': 'stock_transfers',
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='Stock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lot_number', models.CharField(blank=True, default='', max_length=64)),
                ('expiry_date', models.DateField(null=True)),
                ('quantity', models.FloatField(default=0)),
                ('updated_at', models.DateTimeField(null=True)),
                ('product', models.ForeignKey(db_column='product_id', on_delete=django.db.models.deletion.PROTECT, to='api.productref')),
                ('warehouse', models.ForeignKey(db_column='warehouse_id', on_delete=django.db.models.deletion.PROTECT, to='api.warehouse')),
            ],
            options={
                'db_table': 'inventory_lots',
                'ordering': ['id'],
                'unique_together': {('product', 'warehouse', 'lot_number')},
            },
        ),
    ]
