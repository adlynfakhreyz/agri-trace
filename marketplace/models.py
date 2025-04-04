import uuid
from django.db import models
from authentication.models import *

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name
    
    def get_descendants(self, include_self=False):
        descendants = []
        if include_self:
            descendants.append(self)
        children = self.children.all()
        for child in children:
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants


class Product(models.Model):
    product_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    
    def __str__(self):
        return self.name
    
    @property
    def get_rating_count(self):
        # Initialize counts for ratings 1 through 5 as strings (to match template iteration)
        counts = {str(i): 0 for i in range(1, 6)}
        for review in self.reviews.all():
            key = str(review.rating)
            counts[key] += 1
        return counts


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')
    is_primary = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Image for {self.product.name}"


class Cart(models.Model):
    cart_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Cart: {self.cart_id}"
    
    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('cart', 'product')
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    @property
    def subtotal(self):
        return self.product.price * self.quantity


class ShippingService(models.Model):
    shipping_service_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_days = models.PositiveIntegerField()
    
    def __str__(self):
        return self.name


class Order(models.Model):
    ORDER_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    )
    
    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.TextField()
    billing_address = models.TextField()
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    
    def __str__(self):
        return f"Order {self.order_id} - {self.status}"


class OrderItem(models.Model):
    SHIPPING_STATUS_CHOICES = (
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
    )
    
    order_item_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
    shipping_service = models.ForeignKey(ShippingService, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at time of purchase
    shipping_price = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_status = models.CharField(max_length=20, choices=SHIPPING_STATUS_CHOICES, default='processing')
    estimated_delivery = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Item {self.order_item_id} from {self.seller.shop_name}"
    
    @property
    def subtotal(self):
        return self.price * self.quantity + self.shipping_price


class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()  # 1-5 stars
    review_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('product', 'buyer')
    
    def __str__(self):
        return f"Review by {self.buyer.merchant.user.username} for {self.product.name}"


class SellerReview(models.Model):
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='reviews')
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()  # 1-5 stars
    review_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('seller', 'buyer')
    
    def __str__(self):
        return f"Review by {self.buyer.merchant.user.username} for {self.seller.shop_name}"

    

