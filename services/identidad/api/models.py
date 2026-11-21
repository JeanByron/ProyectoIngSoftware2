from django.db import models


class Usuario(models.Model):
    username = models.CharField(max_length=150, unique=True)
    full_name = models.CharField(max_length=200)
    email = models.EmailField(max_length=254)
    role = models.CharField(max_length=20)
    warehouse_ids = models.JSONField(default=list)
    active = models.BooleanField(default=True)
    password = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users"
        ordering = ["id"]

    def to_dict(self):
        return {
            "id": self.id, "username": self.username, "fullName": self.full_name, "email": self.email,
            "role": self.role, "warehouseIds": self.warehouse_ids, "active": self.active,
            "createdAt": self.created_at.isoformat(),
        }
