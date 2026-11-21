import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='PurchaseOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(blank=True, max_length=30)),
                ('destination_warehouse_id', models.CharField(max_length=10)),
                ('status', models.CharField(max_length=30)),
                ('total', models.FloatField(default=0)),
                ('expected_delivery_date', models.DateField(null=True)),
                ('history', models.JSONField(default=list)),
                ('created_by', models.BigIntegerField()),
                ('approved_by', models.BigIntegerField(null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'purchase_orders',
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='Supplier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nit', models.CharField(max_length=30, unique=True)),
                ('name', models.CharField(max_length=200)),
                ('type', models.CharField(max_length=30, null=True)),
                ('contact_name', models.CharField(max_length=200, null=True)),
                ('email', models.CharField(max_length=254, null=True)),
                ('phone', models.CharField(max_length=50, null=True)),
                ('city', models.CharField(max_length=100, null=True)),
                ('default_lead_time_days', models.IntegerField(null=True)),
                ('active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'suppliers',
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='Receipt',
            fields=[
                ('id', models.CharField(max_length=255, primary_key=True, serialize=False)),
                ('warehouse_id', models.CharField(max_length=10)),
                ('delivery_note', models.CharField(max_length=255, null=True)),
                ('lines', models.JSONField(default=list)),
                ('inventory_movement_ids', models.JSONField(default=list)),
                ('received_by', models.BigIntegerField()),
                ('received_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(db_column='purchase_order_id', on_delete=django.db.models.deletion.PROTECT, related_name='receipts', to='api.purchaseorder')),
            ],
            options={
                'db_table': 'receipts',
                'ordering': ['received_at'],
            },
        ),
        migrations.AddField(
            model_name='purchaseorder',
            name='supplier',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='api.supplier'),
        ),
        migrations.CreateModel(
            name='PurchaseOrderLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('line_number', models.IntegerField()),
                ('product_id', models.CharField(max_length=64)),
                ('product_code', models.CharField(max_length=50)),
                ('product_name', models.CharField(max_length=200)),
                ('unit', models.CharField(max_length=20)),
                ('requires_lot', models.BooleanField(default=False)),
                ('quantity', models.FloatField()),
                ('received_quantity', models.FloatField(default=0)),
                ('pending_quantity', models.FloatField()),
                ('unit_price', models.FloatField()),
                ('subtotal', models.FloatField()),
                ('order', models.ForeignKey(db_column='purchase_order_id', on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='api.purchaseorder')),
            ],
            options={
                'db_table': 'purchase_order_items',
                'ordering': ['line_number'],
                'unique_together': {('order', 'line_number')},
            },
        ),
    ]
