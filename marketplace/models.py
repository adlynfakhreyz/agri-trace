from django.db import models
from auth.models import Merchant, Buyer, Seller

# Create your models here.
class Product(models.Model):
    product_id = models.UUIDField(primary_key=True)
    seller_id = models.ForeignKey(Seller, on_delete=models.CASCADE, null=False, blank=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()

    def __str__(self):
        return self.name
    

class BuyingTransaction(models.Model):
    buying_transaction_id = models.UUIDField(primary_key=True)
    buyer_id = models.ForeignKey(Buyer, on_delete=models.CASCADE, null=False, blank=False)
    date = models.DateTimeField(auto_now_add=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_location = models.CharField(max_length=255)
    payment_status = models.CharField(max_length=50)

    def __str__(self):
        return f"Transaction {self.buying_transaction_id} - {self.payment_status}"

class ShippingService(models.Model):
    shipping_service_id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Subtransaction(models.Model):
    subtransaction_id = models.UUIDField(primary_key=True)
    buying_transaction_id = models.ForeignKey(BuyingTransaction, on_delete=models.CASCADE, null=False, blank=False)
    shipping_service_id = models.ForeignKey(ShippingService, on_delete=models.CASCADE, null=False, blank=False)
    subtotal_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    shipping_status = models.CharField(max_length=255)
    shipping_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    eta = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Subtransaction {self.subtransaction_id}"

    

