import uuid
from django.conf import settings
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.utils import timezone
from django.utils.text import slugify
from unittest.mock import patch, MagicMock, PropertyMock
from decimal import Decimal
import json
import requests

# Import models from marketplace and other apps
from authentication.models import Merchant, Buyer, Seller # Assuming these are in authentication
from .models import (
    Category, Product, ProductImage, Cart, CartItem, Order, OrderItem,
    ShippingService, ProductReview, SellerReview
)
# Import forms
from .forms import (
    SellerRegistrationForm, ProductForm, ProductImageFormSet, CartAddProductForm,
    ShippingAddressForm, AgriPayLinkForm, AgriPayPaymentForm, ProductSearchForm,
    MerchantForm, BuyerForm
)
from marketplace import forms

User = get_user_model()

# --- Mock Response Helper ---
class MockResponse:
    def __init__(self, json_data, status_code):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code} Error")

# --- Test Setup ---
class MarketplaceTestBase(TestCase):
    """Base class with common setup for marketplace tests."""

    @classmethod
    def setUpTestData(cls):
        """Set up data once for all tests in derived classes."""
        cls.client = Client()
        cls.password = 'TestPass123!'

        # User 1: Buyer Only
        cls.user_buyer = User.objects.create_user(username='buyeronly', password=cls.password, email='buyer@test.com')
        cls.merchant_buyer = Merchant.objects.create(user=cls.user_buyer)
        cls.buyer = Buyer.objects.create(merchant=cls.merchant_buyer, location="Buyer City")

        # User 2: Seller & Buyer
        cls.user_seller = User.objects.create_user(username='testseller', password=cls.password, email='seller@test.com')
        # Add AgriPay fields needed for testing wallet views
        cls.user_seller.has_agripay_wallet = False
        cls.user_seller.agripay_token = None
        cls.user_seller.save() # Save the extra fields
        cls.merchant_seller = Merchant.objects.create(user=cls.user_seller)
        cls.buyer_seller = Buyer.objects.create(merchant=cls.merchant_seller, location="Seller Town")
        cls.seller = Seller.objects.create(merchant=cls.merchant_seller, shop_name="Test Shop")

        # User 3: Another user for ownership checks
        cls.user_other = User.objects.create_user(username='otheruser', password=cls.password, email='other@test.com')
        cls.merchant_other = Merchant.objects.create(user=cls.user_other)
        cls.buyer_other = Buyer.objects.create(merchant=cls.merchant_other)

        # Categories
        cls.cat_parent = Category.objects.create(name="Electronics", slug="electronics")
        cls.cat_child = Category.objects.create(name="Mobile Phones", slug="mobile-phones", parent=cls.cat_parent)

        # Product by cls.seller
        cls.product1 = Product.objects.create(
            seller=cls.seller,
            category=cls.cat_child,
            name="Test Phone",
            slug="test-phone",
            description="A test phone",
            price=Decimal("500.00"),
            stock=10,
            is_active=True
        )
        cls.product1_image = ProductImage.objects.create(product=cls.product1, is_primary=True) # Assuming image field optional for test

        # Another product
        cls.product2 = Product.objects.create(
            seller=cls.seller,
            category=cls.cat_child,
            name="Another Gadget",
            slug="another-gadget",
            description="Another cool gadget",
            price=Decimal("50.00"),
            stock=5,
            is_active=True,
            is_featured=True
        )

        # Inactive product
        cls.product_inactive = Product.objects.create(
            seller=cls.seller, category=cls.cat_child, name="Inactive Gadget", slug="inactive-gadget",
            price=Decimal("10.00"), stock=1, is_active=False
        )

        # Shipping Service
        cls.shipping_service = ShippingService.objects.create(
            name="Standard Shipping", base_price=Decimal("5.00"), estimated_days=5
        )

        # URLs (adjust app_name 'marketplace' if different)
        cls.homepage_url = reverse('marketplace:marketplace')
        cls.profile_url = reverse('marketplace:profile')
        cls.edit_profile_url = reverse('marketplace:edit_profile')
        cls.become_seller_url = reverse('marketplace:become_seller')
        cls.seller_dashboard_url = reverse('marketplace:seller_dashboard')
        cls.add_product_url = reverse('marketplace:add_product')
        cls.edit_product_url = reverse('marketplace:edit_product', args=[cls.product1.product_id])
        cls.delete_product_url = reverse('marketplace:delete_product', args=[cls.product1.product_id])
        cls.product_list_url = reverse('marketplace:product_list')
        cls.product_detail_url = reverse('marketplace:product_detail', args=[cls.product1.product_id, cls.product1.slug])
        cls.store_detail_url = reverse('marketplace:store_detail', args=[cls.seller.id])
        cls.cart_add_url = reverse('marketplace:cart_add', args=[cls.product1.product_id])
        cls.cart_remove_url = reverse('marketplace:cart_remove', args=[cls.product1.product_id])
        cls.cart_detail_url = reverse('marketplace:cart_detail')
        cls.checkout_url = reverse('marketplace:checkout')
        cls.link_agripay_url = reverse('marketplace:link_agripay')
        # URLs requiring IDs created during tests (order, review) will be constructed in tests
        cls.my_orders_url = reverse('marketplace:my_orders')
        cls.seller_orders_url = reverse('marketplace:seller_orders')
        cls.wallet_balance_url = reverse('marketplace:wallet_balance')
        cls.wallet_topup_url = reverse('marketplace:wallet_topup')
        cls.login_url = reverse('login') # Assuming login URL name is 'login'

    def _login_user(self, user):
        """Helper to log in a specific user."""
        self.client.login(username=user.username, password=self.password)

    def _assert_login_required(self, url, method='get', data=None, **kwargs):
        """Helper to check if login is required."""
        if method == 'get':
            response = self.client.get(url, **kwargs)
        elif method == 'post':
            response = self.client.post(url, data=data or {}, **kwargs)
        self.assertRedirects(response, f'{self.login_url}?next={url}')

    def _create_cart_item(self, buyer_profile, product, quantity=1):
        """Helper to create a cart item."""
        cart, _ = Cart.objects.get_or_create(buyer=buyer_profile)
        item, _ = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': quantity})
        if not _: # if not created
            item.quantity = quantity
            item.save()
        return item

    def _create_order(self, buyer_profile, status='pending', product=None, quantity=1, price=None):
        """Helper to create a simple order and order item."""
        product = product or self.product1
        price = price or product.price
        total_price = price * quantity # Simplified, ignoring shipping for this helper

        order = Order.objects.create(
            buyer=buyer_profile,
            total_price=total_price,
            shipping_address="Test Address",
            billing_address="Test Address",
            status=status
        )
        order_item = OrderItem.objects.create(
            order=order,
            product=product,
            seller=product.seller,
            shipping_service=self.shipping_service,
            quantity=quantity,
            price=price,
            shipping_price = self.shipping_service.base_price # Add shipping price
        )
        return order, order_item

# --- Test General Views ---
class GeneralMarketplaceViewsTests(MarketplaceTestBase):

    def test_homepage_view(self):
        self._login_user(self.user_buyer)
        response = self.client.get(self.homepage_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/marketplace.html')
        self.assertIn('featured_products', response.context)
        self.assertIn('new_arrivals', response.context)
        self.assertIn('top_sellers', response.context)
        self.assertIn('top_categories', response.context)
        # Check if buyer was created for the logged-in user if they didn't have one
        self.assertTrue(Buyer.objects.filter(merchant__user=self.user_buyer).exists())

    def test_profile_view(self):
        self._login_user(self.user_seller) # User with all profiles
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/profile.html')
        self.assertTrue(response.context['is_seller'])
        self.assertEqual(response.context['seller'], self.seller)
        self.assertEqual(response.context['buyer'], self.buyer_seller)

    def test_profile_view_buyer_only(self):
        self._login_user(self.user_buyer)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/profile.html')
        self.assertFalse(response.context['is_seller'])
        self.assertIsNone(response.context['seller'])
        self.assertEqual(response.context['buyer'], self.buyer)

    def test_edit_profile_view_get(self):
        self._login_user(self.user_buyer)
        response = self.client.get(self.edit_profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/edit_profile.html')
        self.assertIsInstance(response.context['merchant_form'], MerchantForm)
        self.assertIsInstance(response.context['buyer_form'], BuyerForm)

    def test_edit_profile_view_post(self):
        self._login_user(self.user_buyer)
        new_location = "New Buyer City"
        new_phone = "1234567890"
        data = {
            'location': new_location,
            'phone_number': new_phone,
            'default_shipping_address': '123 Test St'
            # Add merchant form fields if needed, e.g., for profile_image
        }
        response = self.client.post(self.edit_profile_url, data)
        self.assertRedirects(response, self.profile_url)
        self.buyer.refresh_from_db()
        self.assertEqual(self.buyer.location, new_location)
        self.assertEqual(self.buyer.phone_number, new_phone)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertTrue('updated successfully' in str(messages[0]))

    def test_product_list_view(self):
        response = self.client.get(self.product_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/product_list.html')
        self.assertIn('page_obj', response.context)
        self.assertIn('form', response.context)
        self.assertContains(response, self.product1.name)
        self.assertContains(response, self.product2.name)
        self.assertNotContains(response, self.product_inactive.name) # Check inactive not shown

    def test_product_list_search_filter(self):
        response = self.client.get(self.product_list_url, {'query': 'Phone'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product1.name)
        self.assertNotContains(response, self.product2.name)

    def test_product_list_category_filter(self):
        # Test filtering by child category
        response = self.client.get(self.product_list_url, {'category': self.cat_child.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product1.name) # Belongs to child
        self.assertContains(response, self.product2.name) # Belongs to child

        # Test filtering by parent category (should include child products)
        response_parent = self.client.get(self.product_list_url, {'category': self.cat_parent.id})
        self.assertEqual(response_parent.status_code, 200)
        self.assertContains(response_parent, self.product1.name)
        self.assertContains(response_parent, self.product2.name)


    def test_product_detail_view(self):
        response = self.client.get(self.product_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/product_detail.html')
        self.assertEqual(response.context['product'], self.product1)
        self.assertIsInstance(response.context['cart_product_form'], CartAddProductForm)

    def test_store_detail_view(self):
        response = self.client.get(self.store_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/store_detail.html')
        self.assertEqual(response.context['seller'], self.seller)
        self.assertIn('page_obj', response.context) # Check pagination context


# --- Test Seller Views ---
class SellerMarketplaceViewsTests(MarketplaceTestBase):

    def test_become_seller_get(self):
        self._login_user(self.user_buyer) # User is not a seller yet
        response = self.client.get(self.become_seller_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/become_seller.html')
        self.assertIsInstance(response.context['form'], SellerRegistrationForm)

    def test_become_seller_already_seller(self):
        self._login_user(self.user_seller) # User is already a seller
        response = self.client.get(self.become_seller_url)
        self.assertRedirects(response, self.seller_dashboard_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('already registered' in str(messages[0]))

    def test_become_seller_post_success(self):
        self._login_user(self.user_buyer)
        data = {
            'shop_name': 'Buyers New Shop',
            'shop_description': 'Selling great stuff'
            # Add file fields if needed and handle them (mock file upload)
        }
        response = self.client.post(self.become_seller_url, data)
        self.assertRedirects(response, self.seller_dashboard_url)
        self.assertTrue(Seller.objects.filter(merchant=self.merchant_buyer).exists())
        new_seller = Seller.objects.get(merchant=self.merchant_buyer)
        self.assertEqual(new_seller.shop_name, 'Buyers New Shop')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('seller account has been created' in str(messages[0]))

    def test_seller_dashboard_access(self):
        # Seller access OK
        self._login_user(self.user_seller)
        response_seller = self.client.get(self.seller_dashboard_url)
        self.assertEqual(response_seller.status_code, 200)
        self.assertTemplateUsed(response_seller, 'marketplace/seller_dashboard.html')
        self.assertIn('products', response_seller.context)
        self.assertIn('recent_orders', response_seller.context)

        # Non-seller access redirects
        self._login_user(self.user_buyer)
        response_buyer = self.client.get(self.seller_dashboard_url)
        self.assertRedirects(response_buyer, self.become_seller_url)

    def test_add_product_get(self):
        self._login_user(self.user_seller)
        response = self.client.get(self.add_product_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/add_product.html')
        self.assertIsInstance(response.context['product_form'], ProductForm)
        self.assertIsInstance(response.context['formset'], forms.BaseInlineFormSet) # Check formset type

    # This is a simplified test focusing on product creation
    def test_add_product_post_success_simple(self):
        self._login_user(self.user_seller)
        product_count_before = Product.objects.filter(seller=self.seller).count()
        new_product_name = "Newly Added Product"
        data = {
            'category': self.cat_child.id,
            'name': new_product_name,
            'description': 'Brand new!',
            'price': '99.99',
            'stock': '50',
            'is_active': 'on',
            # Minimal formset data for no images
            'productimage_set-TOTAL_FORMS': '0',
            'productimage_set-INITIAL_FORMS': '0',
            'productimage_set-MIN_NUM_FORMS': '0',
            'productimage_set-MAX_NUM_FORMS': '1000',
        }
        response = self.client.post(self.add_product_url, data)
        # print(response.context['product_form'].errors) # Uncomment to debug form errors
        # print(response.context['formset'].errors)     # Uncomment to debug formset errors
        self.assertEqual(Product.objects.filter(seller=self.seller).count(), product_count_before + 1)
        new_product = Product.objects.get(seller=self.seller, name=new_product_name)
        self.assertEqual(new_product.slug, slugify(new_product_name)) # Check auto-slug
        self.assertRedirects(response, self.seller_dashboard_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('added successfully' in str(messages[0]))

    def test_edit_product_get(self):
        self._login_user(self.user_seller)
        response = self.client.get(self.edit_product_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/edit_product.html')
        self.assertEqual(response.context['product'], self.product1)
        self.assertEqual(response.context['product_form'].instance, self.product1)

    def test_delete_product_post(self):
        self._login_user(self.user_seller)
        product_id_to_delete = self.product1.product_id
        product_count_before = Product.objects.filter(seller=self.seller).count()

        # Need to use HTTP_X_REQUESTED_WITH for require_POST decorator sometimes? No, just POST method.
        response = self.client.post(self.delete_product_url) # require_POST decorator handles method check

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(Product.objects.filter(seller=self.seller).count(), product_count_before - 1)
        with self.assertRaises(Product.DoesNotExist):
            Product.objects.get(product_id=product_id_to_delete)

    def test_seller_orders_view(self):
        self._login_user(self.user_seller)
        # Create an order item for this seller
        _, order_item = self._create_order(self.buyer, product=self.product1)

        response = self.client.get(self.seller_orders_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/seller_orders.html')
        self.assertIn('page_obj', response.context)
        self.assertContains(response, order_item.product.name)

    def test_update_order_status_post(self):
        self._login_user(self.user_seller)
        _, order_item = self._create_order(self.buyer, product=self.product1, status='paid') # Order must be paid
        order_item.shipping_status = 'processing' # Initial status
        order_item.save()
        update_url = reverse('marketplace:update_order_status', args=[order_item.order_item_id])

        response = self.client.post(update_url, {'status': 'shipped'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['new_status'], 'shipped')
        order_item.refresh_from_db()
        self.assertEqual(order_item.shipping_status, 'shipped')
        # Check parent order status updated
        order_item.order.refresh_from_db()
        self.assertEqual(order_item.order.status, 'shipped')

# --- Test Cart/Checkout Views ---
class CartCheckoutViewsTests(MarketplaceTestBase):

    def test_cart_add(self):
        self._login_user(self.user_buyer)
        cart_item_count_before = CartItem.objects.filter(cart__buyer=self.buyer).count()
        data = {'quantity': 2, 'update': False}
        # Use HTTP_REFERER to simulate coming from product detail page
        response = self.client.post(self.cart_add_url, data, HTTP_REFERER=self.product_detail_url)
        self.assertRedirects(response, self.product_detail_url) # Should redirect back
        self.assertEqual(CartItem.objects.filter(cart__buyer=self.buyer).count(), cart_item_count_before + 1)
        cart_item = CartItem.objects.get(cart__buyer=self.buyer, product=self.product1)
        self.assertEqual(cart_item.quantity, 2)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('added to your cart' in str(messages[0]))

    def test_cart_add_update_quantity(self):
        self._login_user(self.user_buyer)
        self._create_cart_item(self.buyer, self.product1, quantity=1) # Item already exists
        cart_item_count_before = CartItem.objects.filter(cart__buyer=self.buyer).count()
        data = {'quantity': 3, 'update': True} # Update flag is True
        response = self.client.post(self.cart_add_url, data, HTTP_REFERER=self.cart_detail_url)
        self.assertRedirects(response, self.cart_detail_url)
        self.assertEqual(CartItem.objects.filter(cart__buyer=self.buyer).count(), cart_item_count_before) # Count shouldn't change
        cart_item = CartItem.objects.get(cart__buyer=self.buyer, product=self.product1)
        self.assertEqual(cart_item.quantity, 3) # Quantity updated

    def test_cart_add_exceed_stock(self):
        self._login_user(self.user_buyer)
        data = {'quantity': self.product1.stock + 5, 'update': False}
        response = self.client.post(self.cart_add_url, data, HTTP_REFERER=self.product_detail_url)
        self.assertRedirects(response, self.product_detail_url)
        cart_item = CartItem.objects.get(cart__buyer=self.buyer, product=self.product1)
        self.assertEqual(cart_item.quantity, self.product1.stock) # Quantity adjusted to stock
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('adjusted the quantity' in str(messages[1])) # Success msg + Warning msg

    def test_cart_remove(self):
        self._login_user(self.user_buyer)
        self._create_cart_item(self.buyer, self.product1)
        cart_item_count_before = CartItem.objects.filter(cart__buyer=self.buyer).count()
        response = self.client.post(self.cart_remove_url) # Assuming remove uses POST for safety
        self.assertRedirects(response, self.cart_detail_url)
        self.assertEqual(CartItem.objects.filter(cart__buyer=self.buyer).count(), cart_item_count_before - 1)
        self.assertFalse(CartItem.objects.filter(cart__buyer=self.buyer, product=self.product1).exists())

    def test_cart_detail_view(self):
        self._login_user(self.user_buyer)
        self._create_cart_item(self.buyer, self.product1)
        response = self.client.get(self.cart_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/cart_detail.html')
        self.assertIn('cart', response.context)
        self.assertIn('cart_items', response.context)
        self.assertContains(response, self.product1.name)

    def test_checkout_get_empty_cart(self):
        self._login_user(self.user_buyer)
        response = self.client.get(self.checkout_url)
        self.assertRedirects(response, self.cart_detail_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('Your cart is empty' in str(messages[0]))

    def test_checkout_get_with_items(self):
        self._login_user(self.user_buyer)
        self._create_cart_item(self.buyer, self.product1)
        response = self.client.get(self.checkout_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/checkout.html')
        self.assertIn('shipping_form', response.context)
        self.assertIn('sellers_items', response.context)

    def test_checkout_stock_adjustment(self):
        """Test checkout redirects if stock is lower than cart quantity."""
        self._login_user(self.user_buyer)
        cart_item = self._create_cart_item(self.buyer, self.product1, quantity=5)
        self.product1.stock = 3 # Lower stock after adding to cart
        self.product1.save()
        response = self.client.get(self.checkout_url) # GET request triggers check
        self.assertRedirects(response, self.cart_detail_url)
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 3) # Quantity adjusted
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('adjusted to the available stock' in str(messages[0]))

    def test_checkout_post_success(self):
        self._login_user(self.user_buyer)
        cart_item = self._create_cart_item(self.buyer, self.product1, quantity=2)
        stock_before = self.product1.stock
        order_count_before = Order.objects.count()
        order_item_count_before = OrderItem.objects.count()

        data = {
            'shipping_address': '123 Checkout Lane',
            'billing_address': '123 Checkout Lane',
            'same_as_shipping': 'on',
            f'seller_{self.seller.id}': self.shipping_service.shipping_service_id, # Map seller to shipping service ID
            'shipping_service': [self.shipping_service.shipping_service_id], # Select shipping service
            # Add other fields if needed by form
        }
        response = self.client.post(self.checkout_url, data)

        self.assertEqual(Order.objects.count(), order_count_before + 1)
        self.assertEqual(OrderItem.objects.count(), order_item_count_before + 1)
        new_order = Order.objects.latest('created_at')
        self.assertEqual(new_order.buyer, self.buyer)
        self.assertEqual(new_order.status, 'pending')
        self.assertEqual(new_order.total_price, (self.product1.price * 2) + self.shipping_service.base_price)

        # Check OrderItem created correctly
        new_order_item = OrderItem.objects.get(order=new_order)
        self.assertEqual(new_order_item.product, self.product1)
        self.assertEqual(new_order_item.quantity, 2)
        self.assertEqual(new_order_item.shipping_service, self.shipping_service)

        # Check stock updated
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, stock_before - 2)

        # Check cart deleted
        self.assertFalse(Cart.objects.filter(buyer=self.buyer).exists())

        # Check redirect to payment
        self.assertRedirects(response, reverse('marketplace:payment', args=[new_order.order_id]))

# --- Test AgriPay Views (Requires Mocking) ---
# @patch decorator targets where 'requests' is *used* (i.e., in marketplace.views)
@patch('marketplace.views.requests.post')
@patch('marketplace.views.requests.get')
class AgriPayViewsTests(MarketplaceTestBase):

    def test_link_agripay_get(self, mock_get, mock_post):
        self._login_user(self.user_seller) # Use user_seller as they have agripay fields
        self.user_seller.has_agripay_wallet = False # Ensure not linked yet
        self.user_seller.save()

        response = self.client.get(self.link_agripay_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/link_agripay.html')
        self.assertIsInstance(response.context['form'], AgriPayLinkForm)
        # Check username prepopulated and hidden
        self.assertContains(response, f'value="{self.user_seller.username}"', html=True)
        self.assertContains(response, 'type="hidden"', html=True)

    def test_link_agripay_already_linked(self, mock_get, mock_post):
        self._login_user(self.user_seller)
        self.user_seller.has_agripay_wallet = True # Simulate already linked
        self.user_seller.save()
        response = self.client.get(self.link_agripay_url)
        self.assertRedirects(response, self.wallet_balance_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('already have an AgriPay wallet' in str(messages[0]))

    def test_link_agripay_post_link_existing_success(self, mock_get, mock_post):
        """Test linking an existing AgriPay account successfully."""
        self._login_user(self.user_seller)
        self.user_seller.has_agripay_wallet = False
        self.user_seller.save()

        # Mock the sequence: POST to auth endpoint returns 200 with token
        mock_auth_success = MockResponse({'token': 'TEST_TOKEN_123'}, 200)
        mock_post.return_value = mock_auth_success # Simulate successful auth

        data = {'username': self.user_seller.username, 'password': self.password}
        response = self.client.post(self.link_agripay_url, data)

        # Check that requests.post was called correctly for auth
        mock_post.assert_called_once_with(
            f"{settings.AGRIPAY_API_URL}/{settings.AGRIPAY_AUTH_ENDPOINT}",
            data={"username": self.user_seller.username, "password": self.password}
        )

        self.assertRedirects(response, self.wallet_balance_url)
        self.user_seller.refresh_from_db()
        self.assertTrue(self.user_seller.has_agripay_wallet)
        self.assertEqual(self.user_seller.agripay_token, 'TEST_TOKEN_123')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('wallet linked successfully' in str(messages[0]))

    def test_link_agripay_post_create_new_success(self, mock_get, mock_post):
        """Test creating and linking a new AgriPay account."""
        self._login_user(self.user_seller)
        self.user_seller.has_agripay_wallet = False
        self.user_seller.save()

        # Mock the sequence:
        # 1. POST to auth endpoint fails (e.g., 401)
        # 2. POST to signup endpoint succeeds (201)
        # 3. POST to auth endpoint again succeeds (200)
        mock_auth_fail = MockResponse({'error': 'Invalid credentials'}, 401)
        mock_signup_success = MockResponse({'message': 'Account created'}, 201)
        mock_auth_success = MockResponse({'token': 'NEW_TOKEN_456'}, 200)

        # Set up side_effect for multiple calls to mock_post
        mock_post.side_effect = [mock_auth_fail, mock_signup_success, mock_auth_success]

        data = {'username': self.user_seller.username, 'password': self.password, 'initial_balance': '10.00'}
        response = self.client.post(self.link_agripay_url, data)

        # Check calls made
        self.assertEqual(mock_post.call_count, 3)
        # Call 1: Auth attempt
        mock_post.assert_any_call(
             f"{settings.AGRIPAY_API_URL}/{settings.AGRIPAY_AUTH_ENDPOINT}",
             data={"username": self.user_seller.username, "password": self.password}
        )
        # Call 2: Signup attempt
        mock_post.assert_any_call(
            f"{settings.AGRIPAY_API_URL}/auth/signup/",
            json={
                "username": self.user_seller.username,
                "password": self.password,
                "email": self.user_seller.email,
                "initial_balance": "10.00" # Should be string based on view
            }
        )
        # Call 3: Auth attempt after signup
        # assert_any_call used again as the exact same call happens twice in this flow
        mock_post.assert_any_call(
             f"{settings.AGRIPAY_API_URL}/{settings.AGRIPAY_AUTH_ENDPOINT}",
             data={"username": self.user_seller.username, "password": self.password}
        )

        self.assertRedirects(response, self.wallet_balance_url)
        self.user_seller.refresh_from_db()
        self.assertTrue(self.user_seller.has_agripay_wallet)
        self.assertEqual(self.user_seller.agripay_token, 'NEW_TOKEN_456')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('created and linked successfully' in str(messages[0]))


    @patch('marketplace.views.AgriPayClient.get_balance')
    def test_payment_view_get_with_agripay(self, mock_get_balance, mock_api_get, mock_api_post):
        """Test GET payment page when AgriPay is linked."""
        self._login_user(self.user_seller) # Use seller as they have agripay fields
        self.user_seller.has_agripay_wallet = True # Simulate linked wallet
        self.user_seller.save()
        order, _ = self._create_order(self.buyer_seller, status='pending') # Order in pending state
        payment_url = reverse('marketplace:payment', args=[order.order_id])

        # Mock get_balance call
        mock_get_balance.return_value = {'balance': '1000.00'} # Sufficient funds

        response = self.client.get(payment_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/payment.html')
        self.assertEqual(response.context['order'], order)
        self.assertIsNotNone(response.context['agripay_form'])
        self.assertEqual(response.context['wallet_balance'], '1000.00')
        self.assertTrue(response.context['has_sufficient_funds'])
        mock_get_balance.assert_called_once() # Ensure balance check happened

    @patch('marketplace.views.AgriPayClient.process_payment')
    @patch('marketplace.views.AgriPayClient.get_balance') # Also mock balance check on GET
    def test_payment_post_agripay_success(self, mock_get_balance, mock_process_payment, mock_api_get, mock_api_post):
        """Test successful payment using AgriPay."""
        self._login_user(self.user_seller)
        self.user_seller.has_agripay_wallet = True
        self.user_seller.save()
        order, order_item = self._create_order(self.buyer_seller, status='pending', product=self.product1, quantity=1)
        payment_url = reverse('marketplace:payment', args=[order.order_id])
        initial_seller_balance = self.merchant_seller.balance

        # Mock balance check on GET
        mock_get_balance.return_value = {'balance': '1000.00'}
        # Mock successful payment process
        mock_process_payment.return_value = {'status': 'success', 'transaction_id': 'TRANS_AGRI_789'}

        data = {
            'payment_method': 'agripay',
            'password': self.password # From the AgriPayPaymentForm
        }
        response = self.client.post(payment_url, data)

        mock_process_payment.assert_called_once_with(order.total_price, self.password)
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        self.assertTrue(order.payment_id.startswith('AGRIPAY-TRANS_AGRI_789'))

        # Check seller balance updated
        self.merchant_seller.refresh_from_db()
        expected_revenue = order_item.price * order_item.quantity # Revenue for this item
        self.assertEqual(self.merchant_seller.balance, initial_seller_balance + expected_revenue)

        # Check redirect to confirmation
        self.assertRedirects(response, reverse('marketplace:order_confirmation', args=[order.order_id]))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('Payment successful' in str(messages[0]))

    # Add tests for AgriPay payment failure, insufficient funds, etc.
    # Add tests for wallet_topup, wallet_balance (mocking get_balance, get_transactions)

# --- Test Order Views ---
class OrderViewsTests(MarketplaceTestBase):

     def test_order_confirmation_view(self):
        self._login_user(self.user_buyer)
        order, _ = self._create_order(self.buyer, status='paid')
        url = reverse('marketplace:order_confirmation', args=[order.order_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/order_confirmation.html')
        self.assertEqual(response.context['order'], order)

     def test_order_detail_view(self):
        self._login_user(self.user_buyer)
        order, _ = self._create_order(self.buyer, status='paid')
        url = reverse('marketplace:order_detail', args=[order.order_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/order_detail.html')
        self.assertEqual(response.context['order'], order)
        self.assertIn('seller_items', response.context)

     def test_my_orders_view(self):
        self._login_user(self.user_buyer)
        self._create_order(self.buyer, status='delivered')
        self._create_order(self.buyer, status='paid', product=self.product2)
        response = self.client.get(self.my_orders_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/my_orders.html')
        self.assertIn('page_obj', response.context)
        self.assertEqual(len(response.context['orders']), 2)

     def test_cancel_order_get(self):
         self._login_user(self.user_buyer)
         order, _ = self._create_order(self.buyer, status='pending')
         url = reverse('marketplace:cancel_order', args=[order.order_id])
         response = self.client.get(url)
         self.assertEqual(response.status_code, 200)
         self.assertTemplateUsed(response, 'marketplace/cancel_order.html')
         self.assertEqual(response.context['order'], order)

     def test_cancel_order_post_success(self):
         self._login_user(self.user_buyer)
         order, _ = self._create_order(self.buyer, status='pending')
         url = reverse('marketplace:cancel_order', args=[order.order_id])
         response = self.client.post(url)
         self.assertRedirects(response, self.my_orders_url)
         order.refresh_from_db()
         self.assertEqual(order.status, 'cancelled')
         messages = list(get_messages(response.wsgi_request))
         self.assertTrue('order has been cancelled' in str(messages[0]))

     def test_cancel_order_post_not_pending(self):
         self._login_user(self.user_buyer)
         order, _ = self._create_order(self.buyer, status='paid') # Not pending
         url = reverse('marketplace:cancel_order', args=[order.order_id])
         detail_url = reverse('marketplace:order_detail', args=[order.order_id])
         response = self.client.post(url)
         self.assertRedirects(response, detail_url)
         order.refresh_from_db()
         self.assertEqual(order.status, 'paid') # Status unchanged
         messages = list(get_messages(response.wsgi_request))
         self.assertTrue('Only pending orders can be cancelled' in str(messages[0]))


# --- Test Review Views ---
class ReviewViewsTests(MarketplaceTestBase):

    def test_add_product_review_get_requires_purchase(self):
        self._login_user(self.user_buyer) # Hasn't bought product1 yet
        url = reverse('marketplace:add_product_review', args=[self.product1.product_id])
        response = self.client.get(url)
        self.assertRedirects(response, self.product_detail_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('purchase this product before leaving a review' in str(messages[0]))

    def test_add_product_review_get_has_purchased(self):
        self._login_user(self.user_buyer)
        self._create_order(self.buyer, status='delivered', product=self.product1) # Mark as purchased
        url = reverse('marketplace:add_product_review', args=[self.product1.product_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/add_product_review.html')
        self.assertEqual(response.context['product'], self.product1)

    def test_add_product_review_already_reviewed(self):
        self._login_user(self.user_buyer)
        self._create_order(self.buyer, status='delivered', product=self.product1)
        review = ProductReview.objects.create(product=self.product1, buyer=self.buyer, rating=4, review_text="Old review")
        add_url = reverse('marketplace:add_product_review', args=[self.product1.product_id])
        edit_url = reverse('marketplace:edit_product_review', args=[review.id])
        response = self.client.get(add_url)
        self.assertRedirects(response, edit_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('already reviewed this product' in str(messages[0]))

    def test_add_product_review_post_success(self):
        self._login_user(self.user_buyer)
        self._create_order(self.buyer, status='delivered', product=self.product1)
        url = reverse('marketplace:add_product_review', args=[self.product1.product_id])
        review_count_before = ProductReview.objects.count()
        data = {'rating': '5', 'review_text': 'This is a great product!'}
        response = self.client.post(url, data)

        self.assertRedirects(response, self.product_detail_url)
        self.assertEqual(ProductReview.objects.count(), review_count_before + 1)
        new_review = ProductReview.objects.get(product=self.product1, buyer=self.buyer)
        self.assertEqual(new_review.rating, 5)
        self.assertEqual(new_review.review_text, 'This is a great product!')
        # Check product average rating updated (assuming initial rating was 0 or null)
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.average_rating, Decimal('5.00'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('review has been submitted' in str(messages[0]))

    def test_add_product_review_post_invalid_data(self):
        """Test submitting invalid data to add_product_review."""
        self._login_user(self.user_buyer)
        self._create_order(self.buyer, status='delivered', product=self.product1)
        url = reverse('marketplace:add_product_review', args=[self.product1.product_id])
        review_count_before = ProductReview.objects.count()

        # Case 1: Invalid rating (too low)
        data_low_rating = {'rating': '0', 'review_text': 'Valid review text here.'}
        response_low = self.client.post(url, data_low_rating)
        self.assertEqual(ProductReview.objects.count(), review_count_before) # No review created
        self.assertEqual(response_low.status_code, 200) # Should re-render the form page
        messages_low = list(get_messages(response_low.wsgi_request))
        self.assertTrue('valid rating between 1 and 5' in str(messages_low[0]))

        # Case 2: Invalid rating (too high)
        data_high_rating = {'rating': '6', 'review_text': 'Valid review text here.'}
        response_high = self.client.post(url, data_high_rating)
        self.assertEqual(ProductReview.objects.count(), review_count_before)
        self.assertEqual(response_high.status_code, 200)
        messages_high = list(get_messages(response_high.wsgi_request))
        self.assertTrue('valid rating between 1 and 5' in str(messages_high[0]))

        # Case 3: Invalid rating (not a number)
        data_nan_rating = {'rating': 'abc', 'review_text': 'Valid review text here.'}
        response_nan = self.client.post(url, data_nan_rating)
        self.assertEqual(ProductReview.objects.count(), review_count_before)
        self.assertEqual(response_nan.status_code, 200)
        messages_nan = list(get_messages(response_nan.wsgi_request))
        self.assertTrue('valid rating between 1 and 5' in str(messages_nan[0]))

        # Case 4: Review text too short
        data_short_text = {'rating': '4', 'review_text': 'Too short'}
        response_short = self.client.post(url, data_short_text)
        self.assertEqual(ProductReview.objects.count(), review_count_before)
        self.assertEqual(response_short.status_code, 200)
        messages_short = list(get_messages(response_short.wsgi_request))
        self.assertTrue('at least 10 characters' in str(messages_short[0]))

        # Case 5: Review text empty
        data_empty_text = {'rating': '4', 'review_text': ' '}
        response_empty = self.client.post(url, data_empty_text)
        self.assertEqual(ProductReview.objects.count(), review_count_before)
        self.assertEqual(response_empty.status_code, 200)
        messages_empty = list(get_messages(response_empty.wsgi_request))
        self.assertTrue('at least 10 characters' in str(messages_empty[0]))

    # --- Seller Review Tests ---

    def test_add_seller_review_get_requires_purchase(self):
        """Test accessing add_seller_review requires purchasing from the seller."""
        self._login_user(self.user_buyer) # Hasn't bought from self.seller yet
        url = reverse('marketplace:add_seller_review', args=[self.seller.id])
        response = self.client.get(url)
        self.assertRedirects(response, self.store_detail_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('purchase from this seller before leaving a review' in str(messages[0]))

    def test_add_seller_review_get_has_purchased(self):
        """Test GET add_seller_review is successful after purchase."""
        self._login_user(self.user_buyer)
        self._create_order(self.buyer, status='delivered', product=self.product1) # Purchase from self.seller
        url = reverse('marketplace:add_seller_review', args=[self.seller.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/add_seller_review.html')
        self.assertEqual(response.context['seller'], self.seller)

    def test_add_seller_review_already_reviewed(self):
        """Test accessing add_seller_review redirects to edit if already reviewed."""
        self._login_user(self.user_buyer)
        self._create_order(self.buyer, status='delivered', product=self.product1)
        review = SellerReview.objects.create(seller=self.seller, buyer=self.buyer, rating=3, review_text="Okay seller")
        add_url = reverse('marketplace:add_seller_review', args=[self.seller.id])
        edit_url = reverse('marketplace:edit_seller_review', args=[review.id])
        response = self.client.get(add_url)
        self.assertRedirects(response, edit_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('already reviewed this seller' in str(messages[0]))

    def test_add_seller_review_post_success(self):
        """Test successfully adding a seller review."""
        self._login_user(self.user_buyer)
        self._create_order(self.buyer, status='delivered', product=self.product1)
        url = reverse('marketplace:add_seller_review', args=[self.seller.id])
        review_count_before = SellerReview.objects.count()
        # Assume initial seller rating is 0 or null for simplicity
        self.seller.rating = Decimal("0.00")
        self.seller.save()

        data = {'rating': '4', 'review_text': 'Good communication and fast shipping!'}
        response = self.client.post(url, data)

        self.assertRedirects(response, self.store_detail_url)
        self.assertEqual(SellerReview.objects.count(), review_count_before + 1)
        new_review = SellerReview.objects.get(seller=self.seller, buyer=self.buyer)
        self.assertEqual(new_review.rating, 4)
        self.assertEqual(new_review.review_text, 'Good communication and fast shipping!')
        # Check seller average rating updated
        self.seller.refresh_from_db()
        self.assertEqual(self.seller.rating, Decimal('4.00'))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('review has been submitted' in str(messages[0]))

    def test_add_seller_review_post_invalid_data(self):
        """Test submitting invalid data to add_seller_review."""
        self._login_user(self.user_buyer)
        self._create_order(self.buyer, status='delivered', product=self.product1)
        url = reverse('marketplace:add_seller_review', args=[self.seller.id])
        review_count_before = SellerReview.objects.count()

        # Case 1: Invalid rating
        data_invalid_rating = {'rating': '6', 'review_text': 'Valid text'}
        response_invalid_rating = self.client.post(url, data_invalid_rating)
        self.assertEqual(SellerReview.objects.count(), review_count_before)
        self.assertEqual(response_invalid_rating.status_code, 200) # Re-renders form
        messages_rating = list(get_messages(response_invalid_rating.wsgi_request))
        self.assertTrue('valid rating between 1 and 5' in str(messages_rating[0]))

        # Case 2: Invalid text
        data_invalid_text = {'rating': '5', 'review_text': 'Short'}
        response_invalid_text = self.client.post(url, data_invalid_text)
        self.assertEqual(SellerReview.objects.count(), review_count_before)
        self.assertEqual(response_invalid_text.status_code, 200) # Re-renders form
        messages_text = list(get_messages(response_invalid_text.wsgi_request))
        self.assertTrue('at least 10 characters' in str(messages_text[0]))

    # --- Edit Review Tests ---

    def test_edit_product_review_get(self):
        """Test GET request for editing an existing product review."""
        self._login_user(self.user_buyer)
        review = ProductReview.objects.create(product=self.product1, buyer=self.buyer, rating=3, review_text="Initial review")
        url = reverse('marketplace:edit_product_review', args=[review.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/edit_product_review.html')
        self.assertEqual(response.context['review'], review)
        self.assertEqual(response.context['product'], self.product1)

    def test_edit_product_review_get_not_owner(self):
        """Test cannot edit another user's product review."""
        # user_buyer creates review
        review = ProductReview.objects.create(product=self.product1, buyer=self.buyer, rating=3, review_text="Buyer's review")
        url = reverse('marketplace:edit_product_review', args=[review.id])
        # other_user tries to access
        self._login_user(self.user_other)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404) # get_object_or_404 fails

    def test_edit_product_review_post_success(self):
        """Test successfully editing a product review."""
        self._login_user(self.user_buyer)
        review = ProductReview.objects.create(product=self.product1, buyer=self.buyer, rating=3, review_text="Initial review")
        # Add another review to test average calculation
        ProductReview.objects.create(product=self.product1, buyer=self.buyer_seller, rating=5, review_text="Seller's review")
        self.product1.average_rating = Decimal('4.00') # (3+5)/2
        self.product1.save()

        url = reverse('marketplace:edit_product_review', args=[review.id])
        updated_text = "This is the updated review text, much better!"
        updated_rating = 5
        data = {'rating': str(updated_rating), 'review_text': updated_text}
        response = self.client.post(url, data)

        self.assertRedirects(response, self.product_detail_url)
        review.refresh_from_db()
        self.assertEqual(review.rating, updated_rating)
        self.assertEqual(review.review_text, updated_text)
        # Check product average rating updated
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.average_rating, Decimal('5.00')) # (5+5)/2
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('review has been updated' in str(messages[0]))

    def test_edit_product_review_post_invalid_data(self):
        """Test submitting invalid data when editing a product review."""
        self._login_user(self.user_buyer)
        review = ProductReview.objects.create(product=self.product1, buyer=self.buyer, rating=3, review_text="Initial review")
        url = reverse('marketplace:edit_product_review', args=[review.id])

        # Case 1: Invalid rating
        data_invalid_rating = {'rating': '0', 'review_text': 'Valid text'}
        response_invalid_rating = self.client.post(url, data_invalid_rating)
        self.assertEqual(response_invalid_rating.status_code, 200) # Re-renders edit form
        messages_rating = list(get_messages(response_invalid_rating.wsgi_request))
        self.assertTrue('valid rating between 1 and 5' in str(messages_rating[0]))
        review.refresh_from_db()
        self.assertEqual(review.rating, 3) # Rating not changed

        # Case 2: Invalid text
        data_invalid_text = {'rating': '2', 'review_text': 'Short'}
        response_invalid_text = self.client.post(url, data_invalid_text)
        self.assertEqual(response_invalid_text.status_code, 200) # Re-renders edit form
        messages_text = list(get_messages(response_invalid_text.wsgi_request))
        self.assertTrue('at least 10 characters' in str(messages_text[0]))
        review.refresh_from_db()
        self.assertEqual(review.review_text, "Initial review") # Text not changed

    def test_edit_seller_review_get(self):
        """Test GET request for editing an existing seller review."""
        self._login_user(self.user_buyer)
        review = SellerReview.objects.create(seller=self.seller, buyer=self.buyer, rating=2, review_text="Seller initial review")
        url = reverse('marketplace:edit_seller_review', args=[review.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'marketplace/edit_seller_review.html')
        self.assertEqual(response.context['review'], review)
        self.assertEqual(response.context['seller'], self.seller)

    def test_edit_seller_review_get_not_owner(self):
        """Test cannot edit another user's seller review."""
        review = SellerReview.objects.create(seller=self.seller, buyer=self.buyer, rating=2, review_text="Buyer's review")
        url = reverse('marketplace:edit_seller_review', args=[review.id])
        # other_user tries to access
        self._login_user(self.user_other)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_edit_seller_review_post_success(self):
        """Test successfully editing a seller review."""
        self._login_user(self.user_buyer)
        review = SellerReview.objects.create(seller=self.seller, buyer=self.buyer, rating=2, review_text="Seller initial review")
        # Add another review
        SellerReview.objects.create(seller=self.seller, buyer=self.buyer_seller, rating=4, review_text="Another buyer's review")
        self.seller.rating = Decimal('3.00') # (2+4)/2
        self.seller.save()

        url = reverse('marketplace:edit_seller_review', args=[review.id])
        updated_text = "Much improved service now!"
        updated_rating = 5
        data = {'rating': str(updated_rating), 'review_text': updated_text}
        response = self.client.post(url, data)

        self.assertRedirects(response, self.store_detail_url)
        review.refresh_from_db()
        self.assertEqual(review.rating, updated_rating)
        self.assertEqual(review.review_text, updated_text)
        # Check seller average rating updated
        self.seller.refresh_from_db()
        self.assertEqual(self.seller.rating, Decimal('4.50')) # (5+4)/2
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('review has been updated' in str(messages[0]))

    def test_edit_seller_review_post_invalid_data(self):
        """Test submitting invalid data when editing a seller review."""
        self._login_user(self.user_buyer)
        review = SellerReview.objects.create(seller=self.seller, buyer=self.buyer, rating=2, review_text="Seller initial review")
        url = reverse('marketplace:edit_seller_review', args=[review.id])

        # Case 1: Invalid rating
        data_invalid_rating = {'rating': 'abc', 'review_text': 'Valid text'}
        response_invalid_rating = self.client.post(url, data_invalid_rating)
        self.assertEqual(response_invalid_rating.status_code, 200)
        messages_rating = list(get_messages(response_invalid_rating.wsgi_request))
        self.assertTrue('valid rating between 1 and 5' in str(messages_rating[0]))
        review.refresh_from_db()
        self.assertEqual(review.rating, 2) # Rating not changed

        # Case 2: Invalid text
        data_invalid_text = {'rating': '1', 'review_text': ''}
        response_invalid_text = self.client.post(url, data_invalid_text)
        self.assertEqual(response_invalid_text.status_code, 200)
        messages_text = list(get_messages(response_invalid_text.wsgi_request))
        self.assertTrue('at least 10 characters' in str(messages_text[0]))
        review.refresh_from_db()
        self.assertEqual(review.review_text, "Seller initial review") # Text not changed