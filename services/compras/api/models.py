from django.db import models


def _iso(value):
    return value.isoformat() if value else None


class Supplier(models.Model):
    nit = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=30, null=True)
    contact_name = models.CharField(max_length=200, null=True)
    email = models.CharField(max_length=254, null=True)
    phone = models.CharField(max_length=50, null=True)
    city = models.CharField(max_length=100, null=True)
    default_lead_time_days = models.IntegerField(null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "suppliers"
        ordering = ["id"]

    def to_dict(self):
        return {"id": self.id, "nit": self.nit, "name": self.name, "type": self.type,
                "contactName": self.contact_name, "email": self.email, "phone": self.phone, "city": self.city,
                "defaultLeadTimeDays": self.default_lead_time_days, "active": self.active,
                "createdAt": _iso(self.created_at), "updatedAt": _iso(self.updated_at)}


class PurchaseOrder(models.Model):
    number = models.CharField(max_length=30, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    destination_warehouse_id = models.CharField(max_length=10)
    status = models.CharField(max_length=30)
    total = models.FloatField(default=0)
    expected_delivery_date = models.DateField(null=True)
    history = models.JSONField(default=list)
    created_by = models.BigIntegerField()
    approved_by = models.BigIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "purchase_orders"
        ordering = ["id"]

    def to_dict(self):
        return {"id": self.id, "number": self.number, "supplierId": self.supplier_id,
                "supplierName": self.supplier.name, "destinationWarehouseId": self.destination_warehouse_id,
                "status": self.status, "total": self.total,
                "expectedDeliveryDate": _iso(self.expected_delivery_date),
                "lines": [ln.to_dict() for ln in self.lines.all()], "history": self.history,
                "createdBy": self.created_by, "approvedBy": self.approved_by,
                "createdAt": _iso(self.created_at), "updatedAt": _iso(self.updated_at)}


class PurchaseOrderLine(models.Model):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="lines",
                              db_column="purchase_order_id")
    line_number = models.IntegerField()
    product_id = models.CharField(max_length=64)
    product_code = models.CharField(max_length=50)
    product_name = models.CharField(max_length=200)
    unit = models.CharField(max_length=20)
    requires_lot = models.BooleanField(default=False)
    quantity = models.FloatField()
    received_quantity = models.FloatField(default=0)
    pending_quantity = models.FloatField()
    unit_price = models.FloatField()
    subtotal = models.FloatField()

    class Meta:
        db_table = "purchase_order_items"
        unique_together = [("order", "line_number")]
        ordering = ["line_number"]

    def to_dict(self):
        return {"id": self.line_number, "productId": self.product_id, "productCode": self.product_code,
                "productName": self.product_name, "unit": self.unit, "requiresLot": self.requires_lot,
                "quantity": self.quantity, "receivedQuantity": self.received_quantity,
                "pendingQuantity": self.pending_quantity, "unitPrice": self.unit_price, "subtotal": self.subtotal}


class Receipt(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="receipts",
                              db_column="purchase_order_id")
    warehouse_id = models.CharField(max_length=10)
    delivery_note = models.CharField(max_length=255, null=True)
    lines = models.JSONField(default=list)
    inventory_movement_ids = models.JSONField(default=list)
    received_by = models.BigIntegerField()
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "receipts"
        ordering = ["received_at"]

    def to_dict(self):
        return {"id": self.id, "purchaseOrderId": self.order_id, "warehouseId": self.warehouse_id,
                "deliveryNote": self.delivery_note, "lines": self.lines,
                "inventoryMovementIds": self.inventory_movement_ids, "receivedBy": self.received_by,
                "receivedAt": _iso(self.received_at)}
