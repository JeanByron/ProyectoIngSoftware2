from django.db import models


class IdempotencyRecord(models.Model):
    path = models.CharField(max_length=255)
    key = models.CharField(max_length=255)
    status = models.IntegerField()
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "idempotency_records"
        unique_together = [("path", "key")]


class Warehouse(models.Model):
    id = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "warehouses"
        ordering = ["id"]

    def to_dict(self):
        return {"id": self.id, "name": self.name, "type": self.type, "active": self.active}


class ProductRef(models.Model):
    product_id = models.CharField(max_length=64, primary_key=True)
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    unit = models.CharField(max_length=20)
    requires_lot = models.BooleanField(default=False)

    class Meta:
        db_table = "product_refs"

    def to_dict(self):
        return {"productId": self.product_id, "code": self.code, "name": self.name, "unit": self.unit,
                "requiresLot": self.requires_lot}


class Stock(models.Model):
    product = models.ForeignKey(ProductRef, on_delete=models.PROTECT, db_column="product_id")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, db_column="warehouse_id")
    lot_number = models.CharField(max_length=64, default="", blank=True)
    expiry_date = models.DateField(null=True)
    quantity = models.FloatField(default=0)
    updated_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "inventory_lots"
        unique_together = [("product", "warehouse", "lot_number")]
        ordering = ["id"]

    def to_dict(self):
        return {"product": self.product.to_dict(), "warehouseId": self.warehouse_id,
                "lotNumber": self.lot_number or None,
                "expiryDate": self.expiry_date.isoformat() if self.expiry_date else None,
                "quantity": self.quantity,
                "updatedAt": self.updated_at.isoformat() if self.updated_at else None}


class Movement(models.Model):
    type = models.CharField(max_length=20)
    product_id = models.CharField(max_length=64)
    warehouse_id = models.CharField(max_length=10)
    lot_number = models.CharField(max_length=64, null=True)
    quantity = models.FloatField()
    balance_after = models.FloatField()
    reason = models.CharField(max_length=255)
    reference_type = models.CharField(max_length=30, null=True)
    reference_id = models.CharField(max_length=64, null=True)
    user_id = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "movements"
        ordering = ["-id"]

    def to_dict(self):
        return {"id": self.id, "type": self.type, "productId": self.product_id, "warehouseId": self.warehouse_id,
                "lotNumber": self.lot_number, "quantity": self.quantity, "balanceAfter": self.balance_after,
                "reason": self.reason, "referenceType": self.reference_type, "referenceId": self.reference_id,
                "userId": self.user_id, "createdAt": self.created_at.isoformat()}


class Transfer(models.Model):
    origin = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="+", db_column="origin_id")
    destination = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="+",
                                    db_column="destination_id")
    status = models.CharField(max_length=30)
    items = models.JSONField(default=list)
    history = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stock_transfers"
        ordering = ["id"]

    def to_dict(self):
        return {"id": self.id, "originId": self.origin_id, "destinationId": self.destination_id,
                "status": self.status, "items": self.items, "history": self.history,
                "createdAt": self.created_at.isoformat(), "updatedAt": self.updated_at.isoformat()}
