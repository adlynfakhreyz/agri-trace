from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
import pyotp

class User(AbstractUser):
    groups = models.ManyToManyField(
        Group,
        related_name="authentication_users",
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="authentication_users_permissions",
        blank=True
    )
    phone_no = models.CharField(max_length=15, blank=True, null=True)
    otp_secret = models.CharField(max_length=32, blank=True, null=True)
    is_2fa_enabled = models.BooleanField(default=False)
    # Add field for AgriPay API token
    agripay_token = models.CharField(max_length=100, blank=True, null=True)
    # Add field to store if user has a wallet
    has_agripay_wallet = models.BooleanField(default=False)

    def __str__(self):
        return self.username

    def generate_otp_secret(self):
        """Generate and store a new OTP secret"""
        self.otp_secret = pyotp.random_base32()
        self.save()
        return self.otp_secret

    def get_otp_uri(self):
        """Generate provisioning URI for QR code"""
        if not self.otp_secret:
            self.generate_otp_secret()
            
        return pyotp.totp.TOTP(self.otp_secret).provisioning_uri(
            name=self.email,
            issuer_name="AgriTrace"
        )

class Farmer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='farmer')
    farm_name = models.CharField(max_length=255)  # Add other farm-related fields

    def __str__(self):
        return f"Farmer: {self.user.username}"

class Merchant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='merchant')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    profile_image = models.ImageField(upload_to='merchant_profiles/', null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Merchant: {self.user.username}"


class Buyer(models.Model):
    merchant = models.OneToOneField(Merchant, on_delete=models.CASCADE, related_name='buyer')
    location = models.CharField(max_length=255)
    default_shipping_address = models.TextField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    
    def __str__(self):
        return f"Buyer: {self.merchant.user.username}"


class Seller(models.Model):
    merchant = models.OneToOneField(Merchant, on_delete=models.CASCADE, related_name='seller')
    shop_name = models.CharField(max_length=255)
    shop_description = models.TextField(null=True, blank=True)
    shop_logo = models.ImageField(upload_to='shop_logos/', null=True, blank=True)
    shop_banner = models.ImageField(upload_to='shop_banners/', null=True, blank=True)
    verified = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Seller: {self.shop_name}"
    
    @property
    def get_rating_count(self):
        # Initialize counts for ratings 1 through 5 as strings (to match template iteration)
        counts = {str(i): 0 for i in range(1, 6)}
        for review in self.reviews.all():
            key = str(review.rating)
            counts[key] += 1
        return counts
    
    @property
    def get_order_count(self):
        """Get the count of completed orders for this seller"""
        from marketplace.models import OrderItem  # Import here to avoid circular imports
        return OrderItem.objects.filter(
            seller=self,
            order__status__in=['paid', 'shipped', 'delivered']
        ).count()