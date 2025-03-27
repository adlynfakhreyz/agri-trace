from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser

# Base User model
class User(AbstractUser):
    phone_no = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.username

# Merchant model
class Merchant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="merchants")
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Merchant: {self.user.username}"

# Farmer model
class Farmer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="farmers")

    def __str__(self):
        return f"Farmer: {self.user.username}"

# Buyer inherits from Merchant
class Buyer(Merchant):
  
    def __str__(self):
        return f"Buyer: {self.user.username}"

# Seller inherits from Merchant
class Seller(Merchant):
    shop_name = models.CharField(max_length=255)

    def __str__(self):
        return f"Seller: {self.user.username}"
