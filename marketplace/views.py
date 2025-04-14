from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.db import models
import requests

from .models import (
    Product, ProductImage, Cart, CartItem, ProductReview, Seller, Buyer, 
    Merchant, Order, OrderItem, SellerReview, ShippingService, Category
)
from .forms import (
    SellerRegistrationForm, ProductForm, PaymentForm,
    ProductImageFormSet, BuyerForm, MerchantForm, CartAddProductForm,
    ShippingAddressForm, ProductSearchForm
)


from django.contrib.auth.decorators import login_required

@login_required
def homepage(request):
    # Create or get merchant and ensure buyer exists
    merchant, created = Merchant.objects.get_or_create(user=request.user)
    if created:
        # Create buyer automatically when merchant is created
        Buyer.objects.create(merchant=merchant)

    # Rest of your existing homepage code...
    featured_products = Product.objects.filter(
        is_featured=True, is_active=True
    ).select_related('seller').prefetch_related('images')[:8]
    
    new_arrivals = Product.objects.filter(
        is_active=True
    ).order_by('-created_at').select_related('seller').prefetch_related('images')[:8]
    
    top_sellers = Seller.objects.annotate(
        product_count=Count('products'),
        avg_rating=Avg('rating')
    ).filter(product_count__gt=0).order_by('-avg_rating')[:4]
    
    top_categories = Category.objects.annotate(
        product_count=Count('products')
    ).filter(product_count__gt=0).order_by('-product_count')[:6]
    
    context = {
        'featured_products': featured_products,
        'new_arrivals': new_arrivals,
        'top_sellers': top_sellers,
        'top_categories': top_categories,
    }
    
    return render(request, 'marketplace/home.html', context)



@login_required
def profile(request):
    user = request.user
    try:
        merchant = user.merchant
        buyer = merchant.buyer
        try:
            seller = merchant.seller
            is_seller = True
        except Seller.DoesNotExist:
            seller = None
            is_seller = False
    except (Merchant.DoesNotExist, Buyer.DoesNotExist):
        messages.error(request, 'Your profile is not set up correctly. Please contact support.')
        return redirect('marketplace:edit_profile')
    
    context = {
        'user': user,
        'merchant': merchant,
        'buyer': buyer,
        'seller': seller,
        'is_seller': is_seller,
    }
    
    return render(request, 'marketplace/profile.html', context)


@login_required
def edit_profile(request):
    user = request.user
    
    # Get or create merchant (ensures merchant always exists)
    merchant, merchant_created = Merchant.objects.get_or_create(user=user)
    
    # Get or create buyer (ensures buyer always exists)
    buyer, buyer_created = Buyer.objects.get_or_create(merchant=merchant)
    
    if request.method == 'POST':
        merchant_form = MerchantForm(request.POST, request.FILES, instance=merchant)
        buyer_form = BuyerForm(request.POST, instance=buyer)
        
        if merchant_form.is_valid() and buyer_form.is_valid():
            merchant_form.save()
            buyer_form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('marketplace:profile')
    else:
        merchant_form = MerchantForm(instance=merchant)
        buyer_form = BuyerForm(instance=buyer)
    
    context = {
        'merchant_form': merchant_form,
        'buyer_form': buyer_form,
        'merchant': merchant,
        'user': user,
    }
    
    return render(request, 'marketplace/edit_profile.html', context)


@login_required
def become_seller(request):
    user = request.user
    
    try:
        merchant = user.merchant
    except Merchant.DoesNotExist:
        messages.error(request, 'Your profile is not set up correctly. Please contact support.')
        return redirect('marketplace:marketplace')
    
    # Check if user is already a seller
    try:
        merchant.seller
        messages.info(request, 'You are already registered as a seller!')
        return redirect('marketplace:seller_dashboard')
    except Seller.DoesNotExist:
        pass
    
    if request.method == 'POST':
        seller_form = SellerRegistrationForm(request.POST, request.FILES)
        if seller_form.is_valid():
            seller = seller_form.save(commit=False)
            seller.merchant = merchant
            seller.save()
            
            messages.success(request, 'Congratulations! Your seller account has been created. You can now add products to your store.')
            return redirect('marketplace:seller_dashboard')
    else:
        seller_form = SellerRegistrationForm()
    
    return render(request, 'marketplace/become_seller.html', {'form': seller_form})


@login_required
def seller_dashboard(request):
    try:
        seller = request.user.merchant.seller
    except (Merchant.DoesNotExist, AttributeError, Seller.DoesNotExist):
        messages.error(request, 'You need to be registered as a seller to access this page.')
        return redirect('marketplace:become_seller')
    
    # Get seller's products
    products = Product.objects.filter(seller=seller).order_by('-created_at')
    
    # Get recent orders
    recent_orders = OrderItem.objects.filter(
        seller=seller
    ).select_related('order', 'product').order_by('-order__created_at')[:5]
    
    # Get sales statistics
    total_sales = OrderItem.objects.filter(
        seller=seller, 
        order__status__in=['paid', 'shipped', 'delivered']
    ).count()
    
    # Sales in the last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    monthly_sales = OrderItem.objects.filter(
        seller=seller,
        order__status__in=['paid', 'shipped', 'delivered'],
        order__created_at__gte=thirty_days_ago
    ).count()
    
    # Calculate revenue
    total_revenue = OrderItem.objects.filter(
        seller=seller,
        order__status__in=['paid', 'shipped', 'delivered']
    ).aggregate(total=models.Sum(models.F('price') * models.F('quantity')))['total'] or Decimal('0')
    
    context = {
        'seller': seller,
        'products': products,
        'recent_orders': recent_orders,
        'total_sales': total_sales,
        'monthly_sales': monthly_sales,
        'total_revenue': total_revenue,
    }
    
    return render(request, 'marketplace/seller_dashboard.html', context)


@login_required
def add_product(request):
    try:
        seller = request.user.merchant.seller
    except (Merchant.DoesNotExist, AttributeError, Seller.DoesNotExist):
        messages.error(request, 'You need to be registered as a seller to add products.')
        return redirect('marketplace:become_seller')
    
    if request.method == 'POST':
        product_form = ProductForm(request.POST, seller=seller)
        if product_form.is_valid():
            product = product_form.save()
            
            # Handle product images
            formset = ProductImageFormSet(request.POST, request.FILES, instance=product)
            if formset.is_valid():
                formset.save()
                messages.success(request, f'Your product "{product.name}" has been added successfully!')
                return redirect('marketplace:seller_dashboard')
    else:
        product_form = ProductForm(seller=seller)
        formset = ProductImageFormSet()
    
    context = {
        'product_form': product_form,
        'formset': formset,
    }
    
    return render(request, 'marketplace/add_product.html', context)


@login_required
def edit_product(request, product_id):
    try:
        seller = request.user.merchant.seller
    except (Merchant.DoesNotExist, AttributeError, Seller.DoesNotExist):
        messages.error(request, 'You need to be registered as a seller to edit products.')
        return redirect('marketplace:become_seller')
    
    product = get_object_or_404(Product, product_id=product_id, seller=seller)
    
    if request.method == 'POST':
        product_form = ProductForm(request.POST, instance=product, seller=seller)
        if product_form.is_valid():
            product = product_form.save()
            
            # Handle product images
            formset = ProductImageFormSet(request.POST, request.FILES, instance=product)
            if formset.is_valid():
                formset.save()
                messages.success(request, f'Your product "{product.name}" has been updated!')
                return redirect('marketplace:seller_dashboard')
    else:
        product_form = ProductForm(instance=product, seller=seller)
        formset = ProductImageFormSet(instance=product)
    
    context = {
        'product_form': product_form,
        'formset': formset,
        'product': product,
    }
    
    return render(request, 'marketplace/edit_product.html', context)


@login_required
@require_POST
def delete_product(request, product_id):
    try:
        seller = request.user.merchant.seller
    except (Merchant.DoesNotExist, AttributeError, Seller.DoesNotExist):
        return JsonResponse({'success': False, 'message': 'You need to be registered as a seller to delete products.'})
    
    product = get_object_or_404(Product, product_id=product_id, seller=seller)
    product.delete()
    
    return JsonResponse({'success': True, 'message': f'Product "{product.name}" has been deleted successfully.'})


def product_list(request):
    form = ProductSearchForm(request.GET)
    products = Product.objects.filter(is_active=True).select_related('seller', 'category').prefetch_related('images')
    
    if form.is_valid():
        query = form.cleaned_data.get('query')
        category_id = form.cleaned_data.get('category')
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')
        sort_by = form.cleaned_data.get('sort_by')
        
        if query:
            products = products.filter(
                Q(name__icontains=query) | 
                Q(description__icontains=query) |
                Q(seller__shop_name__icontains=query)
            )
        
        if category_id:
            category = get_object_or_404(Category, id=category_id)
            # Get all subcategories
            subcategories = category.get_descendants(include_self=True)
            products = products.filter(category__in=subcategories)
        
        if min_price is not None:
            products = products.filter(price__gte=min_price)
            
        if max_price is not None:
            products = products.filter(price__lte=max_price)
            
        if sort_by == 'price_asc':
            products = products.order_by('price')
        elif sort_by == 'price_desc':
            products = products.order_by('-price')
        elif sort_by == 'newest':
            products = products.order_by('-created_at')
        elif sort_by == 'rating':
            products = products.order_by('-average_rating')
    else:
        # Default sorting
        products = products.order_by('-created_at')
    
    # # Get all categories for the sidebar
    # categories = Category.objects.filter(parent=None).annotate(product_count=Count('products'))

    from collections import defaultdict

    def get_all_descendants(category):
        descendants = []
        children = category.children.all()
        for child in children:
            descendants.append(child)
            descendants.extend(get_all_descendants(child))
        return descendants


    def get_total_product_count(category):
        # Get this category and all its descendants
        descendant_categories = [category] + get_all_descendants(category)
        descendant_ids = [cat.id for cat in descendant_categories]
        return Product.objects.filter(category_id__in=descendant_ids, is_active=True).count()

    # Get top-level categories
    categories = Category.objects.filter(parent=None).prefetch_related('children__children')

    # Attach total product count manually
    for cat in categories:
        cat.product_count = get_total_product_count(cat)
        for child in cat.children.all():
            child.product_count = get_total_product_count(child)

    
    # Pagination
    paginator = Paginator(products, 12)  # 12 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'categories': categories,
    }
    
    return render(request, 'marketplace/product_list.html', context)


def product_detail(request, product_id, slug):
    product = get_object_or_404(
        Product, 
        product_id=product_id, 
        slug=slug,
        is_active=True
    )
    
    # Get related products
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(product_id=product.product_id)[:4]
    
    # Add to cart form
    cart_product_form = CartAddProductForm()
    
    # Check if the user has purchased this product
    has_purchased = False
    has_reviewed = False
    user_review = None
    
    if request.user.is_authenticated:
        try:
            buyer = request.user.merchant.buyer
            # Check if user has purchased this product
            has_purchased = OrderItem.objects.filter(
                product=product,
                order__buyer=buyer,
                order__status__in=['paid', 'shipped', 'delivered']
            ).exists()
            
            # Check if user has already reviewed this product
            try:
                user_review = ProductReview.objects.get(product=product, buyer=buyer)
                has_reviewed = True
            except ProductReview.DoesNotExist:
                pass
                
        except (Merchant.DoesNotExist, Buyer.DoesNotExist, AttributeError):
            pass
    
    # Add method to get rating counts if not defined on Product model
    if not hasattr(product, 'get_rating_count'):
        product.get_rating_count = {
            '1': ProductReview.objects.filter(product=product, rating=1).count(),
            '2': ProductReview.objects.filter(product=product, rating=2).count(),
            '3': ProductReview.objects.filter(product=product, rating=3).count(),
            '4': ProductReview.objects.filter(product=product, rating=4).count(),
            '5': ProductReview.objects.filter(product=product, rating=5).count(),
        }
    
    context = {
        'product': product,
        'related_products': related_products,
        'cart_product_form': cart_product_form,
        'has_purchased': has_purchased,
        'has_reviewed': has_reviewed,
        'user_review': user_review,
    }
    
    return render(request, 'marketplace/product_detail.html', context)


def store_detail(request, seller_id):
    seller = get_object_or_404(Seller, id=seller_id)
    
    # Get seller's products
    products = Product.objects.filter(
        seller=seller,
        is_active=True
    ).order_by('-created_at')
    
    # Check if the user has purchased from this seller
    has_purchased = False
    has_reviewed = False
    user_review = None
    
    if request.user.is_authenticated:
        try:
            buyer = request.user.merchant.buyer
            # Check for completed orders from this seller
            has_purchased = OrderItem.objects.filter(
                seller=seller,
                order__buyer=buyer,
                order__status__in=['paid', 'shipped', 'delivered']
            ).exists()
            
            # Check if the user has already reviewed this seller
            try:
                user_review = SellerReview.objects.get(seller=seller, buyer=buyer)
                has_reviewed = True
            except SellerReview.DoesNotExist:
                pass
        except (Merchant.DoesNotExist, Buyer.DoesNotExist, AttributeError):
            pass
    
    # Pagination
    paginator = Paginator(products, 12)  # 12 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'seller': seller,
        'page_obj': page_obj,
        'has_purchased': has_purchased,
        'has_reviewed': has_reviewed,
        'user_review': user_review,
    }
    
    return render(request, 'marketplace/store_detail.html', context)

@login_required
def cart_add(request, product_id):
    product = get_object_or_404(Product, product_id=product_id)
    form = CartAddProductForm(request.POST)
    
    if form.is_valid():
        quantity = form.cleaned_data['quantity']
        update = form.cleaned_data['update']
        
        try:
            buyer = request.user.merchant.buyer
        except (Merchant.DoesNotExist, AttributeError, Buyer.DoesNotExist):
            messages.error(request, 'Your profile is not set up correctly. Please contact support.')
            return redirect('marketplace:product_detail', product_id=product_id, slug=product.slug)
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(buyer=buyer)
        
        # Get or create cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created and update:
            cart_item.quantity = quantity
        elif not created:
            cart_item.quantity += quantity
        
        # Make sure we don't exceed available stock
        if cart_item.quantity > product.stock:
            cart_item.quantity = product.stock
            messages.warning(request, f"We've adjusted the quantity to the maximum available stock ({product.stock}).")
        
        cart_item.save()
        
        messages.success(request, f'"{product.name}" has been added to your cart.')
        
    return redirect(request.META.get('HTTP_REFERER', 'marketplace:product_list'))


@login_required
def cart_remove(request, product_id):
    product = get_object_or_404(Product, product_id=product_id)
    
    try:
        buyer = request.user.merchant.buyer
        cart = Cart.objects.get(buyer=buyer)
        cart_item = CartItem.objects.get(cart=cart, product=product)
        cart_item.delete()
        messages.success(request, f'"{product.name}" has been removed from your cart.')
    except (Merchant.DoesNotExist, AttributeError, Buyer.DoesNotExist, Cart.DoesNotExist, CartItem.DoesNotExist):
        pass
    
    return redirect('marketplace:cart_detail')


@login_required
def cart_detail(request):
    try:
        buyer = request.user.merchant.buyer
        cart, created = Cart.objects.get_or_create(buyer=buyer)
        cart_items = cart.items.all().select_related('product', 'product__seller')
    except (Merchant.DoesNotExist, AttributeError, Buyer.DoesNotExist):
        cart_items = []
        cart = None
    
    for item in cart_items:
        item.update_form = CartAddProductForm(initial={'quantity': item.quantity, 'update': True})
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
    }
    
    return render(request, 'marketplace/cart_detail.html', context)



@login_required
def checkout(request):
    try:
        buyer = request.user.merchant.buyer
        cart = Cart.objects.get(buyer=buyer)
        cart_items = cart.items.all().select_related('product', 'product__seller')
    except (Cart.DoesNotExist, AttributeError):
        messages.error(request, 'Your cart is empty.')
        return redirect('marketplace:cart_detail')
    
    # Check if cart is empty
    if not cart_items:
        messages.error(request, 'Your cart is empty.')
        return redirect('marketplace:cart_detail')
    
    # Check product availability
    for item in cart_items:
        if item.quantity > item.product.stock:
            if item.product.stock == 0:
                messages.error(request, f'"{item.product.name}" is out of stock and has been removed from your cart.')
                item.delete()
            else:
                item.quantity = item.product.stock
                item.save()
                messages.warning(request, f'Quantity for "{item.product.name}" has been adjusted to the available stock ({item.product.stock}).')
            return redirect('marketplace:cart_detail')
    
    # Get shipping services
    shipping_services = ShippingService.objects.all()
    
    # Initialize shipping form
    if buyer.default_shipping_address:
        initial_data = {'shipping_address': buyer.default_shipping_address}
        if request.POST.get('same_as_shipping'):
            initial_data['billing_address'] = buyer.default_shipping_address
        shipping_form = ShippingAddressForm(initial=initial_data)
    else:
        shipping_form = ShippingAddressForm()
    
    # Process form submission
    if request.method == 'POST':
        shipping_form = ShippingAddressForm(request.POST)
        if shipping_form.is_valid():
            shipping_address = shipping_form.cleaned_data['shipping_address']
            billing_address = shipping_form.cleaned_data['billing_address']
            save_default = shipping_form.cleaned_data.get('save_default', False)
            selected_shipping_ids = request.POST.getlist('shipping_service')
            
            # Validate shipping service selection
            if len(selected_shipping_ids) != len(set(item.product.seller.id for item in cart_items)):
                messages.error(request, 'Please select a shipping option for each seller.')
                return redirect('marketplace:checkout')
            
            # Save default address if requested
            if save_default:
                buyer.default_shipping_address = shipping_address
                buyer.save()
            
            # Create order
            total_price = Decimal('0.00')
            for item in cart_items:
                total_price += item.subtotal
            
            # Add shipping costs
            shipping_costs = Decimal('0.00')
            for shipping_id in selected_shipping_ids:
                shipping_service = get_object_or_404(ShippingService, shipping_service_id=shipping_id)
                shipping_costs += shipping_service.base_price
            
            total_price += shipping_costs
            
            # Create the order
            order = Order.objects.create(
                buyer=buyer,
                total_price=total_price,
                shipping_address=shipping_address,
                billing_address=billing_address,
                status='pending'
            )
            
            # Create order items
            seller_to_shipping = {}
            for shipping_id in selected_shipping_ids:
                shipping_service = get_object_or_404(ShippingService, shipping_service_id=shipping_id)
                # For simplicity, we're assuming one shipping method per seller
                seller_id = request.POST.get(f'seller_{shipping_id}')
                seller_to_shipping[seller_id] = shipping_service
            
            for item in cart_items:
                seller_id = str(item.product.seller.id)
                shipping_service = seller_to_shipping.get(seller_id)
                
                if not shipping_service:
                    # Fallback to the first shipping service if mapping fails
                    shipping_service = ShippingService.objects.first()
                
                # Calculate estimated delivery date
                estimated_delivery = timezone.now() + timedelta(days=shipping_service.estimated_days)
                
                # Create order item
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    seller=item.product.seller,
                    shipping_service=shipping_service,
                    quantity=item.quantity,
                    price=item.product.price,
                    shipping_price=shipping_service.base_price,
                    estimated_delivery=estimated_delivery
                )
                
                # Update product stock
                item.product.stock -= item.quantity
                item.product.save()
            
            # Clear the cart
            cart.delete()
            
            # Redirect to payment page
            return redirect('marketplace:payment', order_id=order.order_id)
    
    # Group cart items by seller for shipping selection
    sellers_items = {}
    for item in cart_items:
        seller = item.product.seller
        if seller.id not in sellers_items:
            sellers_items[seller.id] = {'seller': seller, 'items': []}
        sellers_items[seller.id]['items'].append(item)
    
    context = {
        'cart': cart,
        'sellers_items': sellers_items.values(),
        'shipping_services': shipping_services,
        'shipping_form': shipping_form,
    }
    
    return render(request, 'marketplace/checkout.html', context)

from .forms import AgriPayLinkForm, AgriPayPaymentForm
from .agripay import AgriPayClient

@login_required
def link_agripay(request):
    """View to link AgriPay account with AgriTrace"""
    user = request.user
    
    # If user already has AgriPay wallet
    if user.has_agripay_wallet:
        messages.info(request, "You already have an AgriPay wallet linked to your account.")
        return redirect('marketplace:wallet_balance')
        
    if request.method == 'POST':
        # Pre-populate the form with the username to ensure it's always present
        post_data = request.POST.copy()
        if 'username' not in post_data or not post_data['username']:
            post_data['username'] = user.username
            
        form = AgriPayLinkForm(post_data)
        
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            initial_balance = form.cleaned_data.get('initial_balance', 0)
            
            # Base URL for AgriPay API
            base_url = settings.AGRIPAY_API_URL
            
            try:
                # Check if account exists in AgriPay, if not create it
                try:
                    # First try to authenticate with existing credentials
                    auth_response = requests.post(
                        f"{base_url}/{settings.AGRIPAY_AUTH_ENDPOINT}",
                        data={"username": username, "password": password}
                    )
                    
                    if auth_response.status_code == 200:
                        # User exists in AgriPay, save the token
                        token_data = auth_response.json()
                        user.agripay_token = token_data.get('token')
                        user.has_agripay_wallet = True
                        user.save()
                        messages.success(request, "AgriPay wallet linked successfully!")
                        return redirect('marketplace:wallet_balance')
                    else:
                        # User doesn't exist or wrong password, create new account
                        
                        # Call the AgriPay signup endpoint
                        signup_response = requests.post(
                            f"{base_url}/auth/signup/",
                            json={
                                "username": username,
                                "password": password,
                                "email": user.email,
                                "initial_balance": str(initial_balance) if initial_balance else "0.00"
                            }
                        )
                        
                        if signup_response.status_code == 201:
                            # Account created, now get the token
                            auth_response = requests.post(
                                f"{base_url}/{settings.AGRIPAY_AUTH_ENDPOINT}",
                                data={"username": username, "password": password}
                            )
                            
                            if auth_response.status_code == 200:
                                token_data = auth_response.json()
                                user.agripay_token = token_data.get('token')
                                user.has_agripay_wallet = True
                                user.save()
                                messages.success(request, "AgriPay account created and linked successfully!")
                                return redirect('marketplace:wallet_balance')
                            else:
                                messages.error(request, "Account created but couldn't authenticate. Please try logging in later.")
                        else:
                            error_data = signup_response.json()
                            messages.error(request, f"Failed to create AgriPay account: {error_data.get('error', 'Unknown error')}")
                except Exception as e:
                    messages.error(request, f"Error during authentication: {str(e)}")
                    
            except requests.exceptions.RequestException as e:
                messages.error(request, f"Failed to connect to AgriPay service: {str(e)}")
        else:
            # Form validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        # Pre-populate the username field with the current user's username
        form = AgriPayLinkForm(initial={'username': user.username})
    
    return render(request, 'marketplace/link_agripay.html', {'form': form, 'user': user})



@login_required
def payment(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, buyer=request.user.merchant.buyer)
    
    if order.status != 'pending':
        messages.error(request, 'This order has already been processed.')
        return redirect('marketplace:order_detail', order_id=order.order_id)
    
    # Create AgriPay payment form
    agripay_form = None
    wallet_balance = None
    has_sufficient_funds = False
    
    # Check if user has linked AgriPay wallet
    if request.user.has_agripay_wallet:
        agripay_form = AgriPayPaymentForm()
        
        # Get wallet balance
        agripay_client = AgriPayClient(user=request.user)
        try:
            balance_data = agripay_client.get_balance()
            if 'balance' in balance_data:
                wallet_balance = balance_data['balance']
                has_sufficient_funds = float(wallet_balance) >= float(order.total_price)
        except Exception as e:
            messages.warning(request, f"Could not retrieve AgriPay wallet balance: {str(e)}")
    
    # Process payment
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        
        if payment_method == 'agripay' and request.user.has_agripay_wallet:
            # Process payment with AgriPay
            agripay_form = AgriPayPaymentForm(request.POST)
            
            if agripay_form.is_valid():
                password = agripay_form.cleaned_data['password']
                
                # Process payment through AgriPay API
                agripay_client = AgriPayClient(user=request.user)
                payment_result = agripay_client.process_payment(order.total_price, password)
                
                if payment_result.get('status') == 'failed':
                    messages.error(request, f"Payment failed: {payment_result.get('error', 'Unknown error')}")
                else:
                    # Payment successful, update order status
                    order.status = 'paid'
                    order.payment_id = f'AGRIPAY-{payment_result.get("transaction_id", timezone.now().timestamp())}'
                    order.save()
                    
                    # Update merchant balances for each seller
                    for item in order.items.all():
                        seller_merchant = item.seller.merchant
                        # Calculate the seller's revenue (excluding shipping)
                        item_total = item.price * item.quantity
                        
                        # Update seller balance
                        seller_merchant.balance += item_total
                        seller_merchant.save()
                    
                    messages.success(request, 'Payment successful! Your order has been placed.')
                    return redirect('marketplace:order_confirmation', order_id=order.order_id)
                    
        elif payment_method == 'credit_card':
            # Existing credit card payment logic
            # Update order status
            order.status = 'paid'
            order.payment_id = f'SIMULATED-{timezone.now().timestamp()}'
            order.save()
            
            # Update merchant balances for each seller
            for item in order.items.all():
                seller_merchant = item.seller.merchant
                # Calculate the seller's revenue (excluding shipping)
                item_total = item.price * item.quantity
                
                # Update seller balance
                seller_merchant.balance += item_total
                seller_merchant.save()
            
            messages.success(request, 'Payment successful! Your order has been placed.')
            return redirect('marketplace:order_confirmation', order_id=order.order_id)
        else:
            messages.error(request, 'Invalid payment method selected.')
    
    context = {
        'order': order,
        'order_items': order.items.all().select_related('product', 'seller', 'shipping_service'),
        'agripay_form': agripay_form,
        'wallet_balance': wallet_balance,
        'has_sufficient_funds': has_sufficient_funds,
    }
    
    return render(request, 'marketplace/payment.html', context)


@login_required
def wallet_topup(request):
    """View to top up AgriPay wallet"""
    if not request.user.has_agripay_wallet:
        messages.error(request, "You need to link your AgriPay wallet first.")
        return redirect('marketplace:link_agripay')
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be greater than zero.")
                
            # Process top-up through AgriPay API
            agripay_client = AgriPayClient(user=request.user)
            result = agripay_client.topup_wallet(amount)
            
            if 'error' in result:
                messages.error(request, f"Top-up failed: {result['error']}")
            else:
                messages.success(request, f"Successfully topped up {amount} to your AgriPay wallet!")
                return redirect('marketplace:wallet_balance')
                
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
    
    # Get current wallet balance
    wallet_balance = None
    agripay_client = AgriPayClient(user=request.user)
    
    try:
        balance_data = agripay_client.get_balance()
        if 'balance' in balance_data:
            wallet_balance = balance_data['probalance']
    except Exception as e:
        messages.warning(request, f"Could not retrieve wallet balance: {str(e)}")
    
    return render(request, 'marketplace/wallet_topup.html', {'wallet_balance': wallet_balance})

@login_required
def wallet_balance(request):
    """View to display wallet balance and transaction history"""
    from datetime import datetime  # Add this import
    import pytz  # Add this import for timezone handling
    
    if not request.user.has_agripay_wallet:
        messages.error(request, "You need to link your AgriPay wallet first.")
        return redirect('marketplace:link_agripay')
    
    # Get wallet balance and transaction history
    agripay_client = AgriPayClient(user=request.user)
    wallet_balance = None
    transaction_history = []
    monthly_spending = "0.00"
    total_topups = "0.00"
    
    # Get transaction filter parameters from query string
    transaction_type = request.GET.get('type')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    try:
        # Get balance
        balance_data = agripay_client.get_balance()
        if 'balance' in balance_data:
            wallet_balance = balance_data['balance']
        
        # Get transaction history with optional filters
        history_data = agripay_client.get_transactions(
            transaction_type=transaction_type,
            start_date=start_date,
            end_date=end_date,
            limit=25  # Show last 25 transactions
        )
        
        if 'transactions' in history_data:
            transaction_history = history_data['transactions']
            
            # Convert string timestamps to datetime objects
            for transaction in transaction_history:
                if 'timestamp' in transaction and transaction['timestamp']:
                    try:
                        # Parse the timestamp string into a datetime object
                        # Try with microsecond format first
                        transaction['timestamp'] = datetime.strptime(
                            transaction['timestamp'], 
                            "%Y-%m-%d %H:%M:%S.%f"
                        )
                    except ValueError:
                        try:
                            # Try without microsecond format 
                            transaction['timestamp'] = datetime.strptime(
                                transaction['timestamp'], 
                                "%Y-%m-%d %H:%M:%S"
                            )
                        except ValueError:
                            try:
                                # Try ISO format
                                transaction['timestamp'] = datetime.fromisoformat(
                                    transaction['timestamp'].replace('Z', '+00:00')
                                )
                            except (ValueError, AttributeError):
                                # Keep as string if parsing fails
                                pass
            
        # Get statistics
        if 'stats' in history_data:
            stats = history_data['stats']
            monthly_spending = stats.get('monthly_spending', "0.00")
            total_topups = stats.get('total_topups', "0.00")
            
            # Calculate percentage of monthly spending relative to balance
            # This is for the progress bar visualization
            if wallet_balance and float(wallet_balance) > 0 and float(monthly_spending) > 0:
                monthly_percentage = min(100, (float(monthly_spending) / float(wallet_balance)) * 100)
            else:
                monthly_percentage = 0
        else:
            monthly_percentage = 0
        
    except Exception as e:
        messages.warning(request, f"Could not retrieve wallet information: {str(e)}")
        monthly_percentage = 0
    
    context = {
        'wallet_balance': wallet_balance,
        'transaction_history': transaction_history,
        'monthly_spending': monthly_spending,
        'total_topups': total_topups,
        'monthly_percentage': monthly_percentage,
    }
    
    return render(request, 'marketplace/wallet_balance.html', context)

@login_required
def transaction_detail(request, transaction_id):
    """View to display details of a specific transaction"""
    if not request.user.has_agripay_wallet:
        messages.error(request, "You need to link your AgriPay wallet first.")
        return redirect('marketplace:link_agripay')
    
    # Get transaction details from AgriPay API
    agripay_client = AgriPayClient(user=request.user)
    
    try:
        # For the transaction detail endpoint, you would need to add this to the AgriPay API
        # Here's how you would call it:
        response = requests.get(
            f"{settings.AGRIPAY_API_URL}/wallet/transactions/{transaction_id}/",
            headers=agripay_client._get_headers()
        )
        
        if response.status_code == 404:
            messages.error(request, "Transaction not found.")
            return redirect('marketplace:wallet_balance')
            
        transaction_data = response.json()
        
        # Get related data based on transaction type
        related_data = None
        
        if transaction_data['transaction_type'] == 'purchase':
            # If it's a purchase, try to get the order details if available
            order_id = transaction_data.get('reference', '').replace('PURCHASE-', '')
            try:
                # This assumes the reference follows a pattern that includes the order ID
                # You would need to adapt this to your actual reference format
                related_data = Order.objects.filter(
                    order_id=order_id,
                    buyer=request.user.merchant.buyer
                ).first()
            except:
                pass
        
    except Exception as e:
        messages.error(request, f"Could not retrieve transaction details: {str(e)}")
        return redirect('marketplace:wallet_balance')
    
    context = {
        'transaction': transaction_data,
        'related_data': related_data
    }
    
    return render(request, 'marketplace/transaction_detail.html', context)

@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, buyer=request.user.merchant.buyer)
    order_items = order.items.all().select_related('product', 'seller', 'shipping_service')
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    
    return render(request, 'marketplace/order_confirmation.html', context)


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, buyer=request.user.merchant.buyer)
    order_items = order.items.all().select_related('product', 'seller', 'shipping_service')
    
    # Group by seller for better organization
    seller_items = {}
    for item in order_items:
        if item.seller.id not in seller_items:
            seller_items[item.seller.id] = {'seller': item.seller, 'items': []}
        seller_items[item.seller.id]['items'].append(item)
    
    context = {
        'order': order,
        'seller_items': seller_items.values(),
    }
    
    return render(request, 'marketplace/order_detail.html', context)


@login_required
def my_orders(request):
    try:
        buyer = request.user.merchant.buyer
        orders = Order.objects.filter(buyer=buyer).order_by('-created_at')
    except AttributeError:
        orders = []
    
    # Pagination
    paginator = Paginator(orders, 10)  # 10 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'orders': page_obj.object_list,
    }
    
    return render(request, 'marketplace/my_orders.html', context)

@login_required
def seller_orders(request):
    try:
        seller = request.user.merchant.seller
    except (AttributeError, Seller.DoesNotExist):
        messages.error(request, 'You need to be registered as a seller to view orders.')
        return redirect('marketplace:become_seller')
    
    # Get orders for this seller
    order_items = OrderItem.objects.filter(
        seller=seller
    ).select_related('order', 'product', 'shipping_service').order_by('-order__created_at')
    
    # Filter by status if requested
    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        order_items = order_items.filter(shipping_status=status_filter)
    
    # Pagination
    paginator = Paginator(order_items, 20)  # 20 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'order_items': page_obj.object_list,
        'status_filter': status_filter or 'all',
    }
    
    return render(request, 'marketplace/seller_orders.html', context)


@login_required
@require_POST
def update_order_status(request, order_item_id):
    try:
        seller = request.user.merchant.seller
    except (AttributeError, Seller.DoesNotExist):
        return JsonResponse({'success': False, 'message': 'You need to be registered as a seller to update orders.'})
    
    order_item = get_object_or_404(OrderItem, order_item_id=order_item_id, seller=seller)
    new_status = request.POST.get('status')
    
    if new_status not in dict(OrderItem.SHIPPING_STATUS_CHOICES):
        return JsonResponse({'success': False, 'message': 'Invalid status.'})
    
    order_item.shipping_status = new_status
    
    # Update estimated delivery if needed
    if new_status == 'shipped':
        # Calculate new estimated delivery if it was shipped now
        days_to_deliver = order_item.shipping_service.estimated_days
        order_item.estimated_delivery = timezone.now() + timedelta(days=days_to_deliver)
    
    order_item.save()
    
    # Update parent order status if all items have been processed
    order = order_item.order
    all_items = OrderItem.objects.filter(order=order)
    
    if all(item.shipping_status == 'delivered' for item in all_items):
        order.status = 'delivered'
        order.save()
    elif all(item.shipping_status in ['shipped', 'delivered'] for item in all_items):
        order.status = 'shipped'
        order.save()
    
    return JsonResponse({
        'success': True, 
        'message': f'Order status updated to {dict(OrderItem.SHIPPING_STATUS_CHOICES)[new_status]}.',
        'new_status': new_status,
        'estimated_delivery': order_item.estimated_delivery.strftime('%Y-%m-%d') if order_item.estimated_delivery else None
    })


@login_required
def seller_order_detail(request, order_item_id):
    try:
        seller = request.user.merchant.seller
    except (AttributeError, Seller.DoesNotExist):
        messages.error(request, 'You need to be registered as a seller to view order details.')
        return redirect('marketplace:become_seller')
    
    order_item = get_object_or_404(OrderItem, order_item_id=order_item_id, seller=seller)
    order = order_item.order
    
    context = {
        'order_item': order_item,
        'order': order,
    }
    
    return render(request, 'marketplace/seller_order_detail.html', context)

@login_required
def add_product_review(request, product_id):
    product = get_object_or_404(Product, product_id=product_id, is_active=True)
    
    try:
        buyer = request.user.merchant.buyer
    except (AttributeError, Buyer.DoesNotExist):
        messages.error(request, 'You need to be registered as a buyer to leave reviews.')
        return redirect('marketplace:product_detail', product_id=product_id, slug=product.slug)
    
    # Check if user has purchased the product
    has_purchased = OrderItem.objects.filter(
        order__buyer=buyer,
        product=product,
        order__status__in=['delivered', 'paid', 'shipped']
    ).exists()
    
    if not has_purchased:
        messages.error(request, 'You need to purchase this product before leaving a review.')
        return redirect('marketplace:product_detail', product_id=product_id, slug=product.slug)
    
    # Check if user has already reviewed this product
    try:
        existing_review = ProductReview.objects.get(product=product, buyer=buyer)
        messages.info(request, 'You have already reviewed this product. You can edit your review.')
        return redirect('marketplace:edit_product_review', review_id=existing_review.id)
    except ProductReview.DoesNotExist:
        pass
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        review_text = request.POST.get('review_text')
        
        try:
            rating = int(rating)
            if not (1 <= rating <= 5):
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'Please provide a valid rating between 1 and 5.')
            return redirect('marketplace:add_product_review', product_id=product_id)
        
        if not review_text or len(review_text.strip()) < 10:
            messages.error(request, 'Please provide a review with at least 10 characters.')
            return redirect('marketplace:add_product_review', product_id=product_id)
        
        # Create the review
        ProductReview.objects.create(
            product=product,
            buyer=buyer,
            rating=rating,
            review_text=review_text
        )
        
        # Update product average rating
        avg_rating = ProductReview.objects.filter(product=product).aggregate(Avg('rating'))['rating__avg']
        product.average_rating = round(avg_rating, 2)
        product.save()
        
        messages.success(request, 'Your review has been submitted successfully!')
        return redirect('marketplace:product_detail', product_id=product_id, slug=product.slug)
    
    context = {
        'product': product,
    }
    
    return render(request, 'marketplace/add_product_review.html', context)


@login_required
def add_seller_review(request, seller_id):
    seller = get_object_or_404(Seller, id=seller_id)
    
    try:
        buyer = request.user.merchant.buyer
    except (AttributeError, Buyer.DoesNotExist):
        messages.error(request, 'You need to be registered as a buyer to leave reviews.')
        return redirect('marketplace:store_detail', seller_id=seller_id)
    
    # Check if user has purchased from this seller
    has_purchased = OrderItem.objects.filter(
        order__buyer=buyer,
        seller=seller,
        order__status__in=['delivered', 'paid', 'shipped']
    ).exists()
    
    if not has_purchased:
        messages.error(request, 'You need to purchase from this seller before leaving a review.')
        return redirect('marketplace:store_detail', seller_id=seller_id)
    
    # Check if user has already reviewed this seller
    try:
        existing_review = SellerReview.objects.get(seller=seller, buyer=buyer)
        messages.info(request, 'You have already reviewed this seller. You can edit your review.')
        return redirect('marketplace:edit_seller_review', review_id=existing_review.id)
    except SellerReview.DoesNotExist:
        pass
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        review_text = request.POST.get('review_text')
        
        try:
            rating = int(rating)
            if not (1 <= rating <= 5):
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'Please provide a valid rating between 1 and 5.')
            return redirect('marketplace:add_seller_review', seller_id=seller_id)
        
        if not review_text or len(review_text.strip()) < 10:
            messages.error(request, 'Please provide a review with at least 10 characters.')
            return redirect('marketplace:add_seller_review', seller_id=seller_id)
        
        # Create the review
        SellerReview.objects.create(
            seller=seller,
            buyer=buyer,
            rating=rating,
            review_text=review_text
        )
        
        # Update seller average rating
        avg_rating = SellerReview.objects.filter(seller=seller).aggregate(Avg('rating'))['rating__avg']
        seller.rating = round(avg_rating, 2)
        seller.save()
        
        messages.success(request, 'Your review has been submitted successfully!')
        return redirect('marketplace:store_detail', seller_id=seller_id)
    
    context = {
        'seller': seller,
    }
    
    return render(request, 'marketplace/add_seller_review.html', context)


@login_required
def edit_product_review(request, review_id):
    review = get_object_or_404(ProductReview, id=review_id, buyer=request.user.merchant.buyer)
    product = review.product
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        review_text = request.POST.get('review_text')
        
        try:
            rating = int(rating)
            if not (1 <= rating <= 5):
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'Please provide a valid rating between 1 and 5.')
            return redirect('marketplace:edit_product_review', review_id=review_id)
        
        if not review_text or len(review_text.strip()) < 10:
            messages.error(request, 'Please provide a review with at least 10 characters.')
            return redirect('marketplace:edit_product_review', review_id=review_id)
        
        # Update the review
        review.rating = rating
        review.review_text = review_text
        review.save()
        
        # Update product average rating
        avg_rating = ProductReview.objects.filter(product=product).aggregate(Avg('rating'))['rating__avg']
        product.average_rating = round(avg_rating, 2)
        product.save()
        
        messages.success(request, 'Your review has been updated successfully!')
        return redirect('marketplace:product_detail', product_id=product.product_id, slug=product.slug)
    
    context = {
        'review': review,
        'product': product,
    }
    
    return render(request, 'marketplace/edit_product_review.html', context)


@login_required
def edit_seller_review(request, review_id):
    review = get_object_or_404(SellerReview, id=review_id, buyer=request.user.merchant.buyer)
    seller = review.seller
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        review_text = request.POST.get('review_text')
        
        try:
            rating = int(rating)
            if not (1 <= rating <= 5):
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'Please provide a valid rating between 1 and 5.')
            return redirect('marketplace:edit_seller_review', review_id=review_id)
        
        if not review_text or len(review_text.strip()) < 10:
            messages.error(request, 'Please provide a review with at least 10 characters.')
            return redirect('marketplace:edit_seller_review', review_id=review_id)
        
        # Update the review
        review.rating = rating
        review.review_text = review_text
        review.save()
        
        # Update seller average rating
        avg_rating = SellerReview.objects.filter(seller=seller).aggregate(Avg('rating'))['rating__avg']
        seller.rating = round(avg_rating, 2)
        seller.save()
        
        messages.success(request, 'Your review has been updated successfully!')
        return redirect('marketplace:store_detail', seller_id=seller.id)
    
    context = {
        'review': review,
        'seller': seller,
    }
    
    return render(request, 'marketplace/edit_seller_review.html', context)

@login_required
def cancel_order(request, order_id):
    """
    Cancel an order with pending status
    Only the buyer who placed the order can cancel it
    """
    order = get_object_or_404(Order, order_id=order_id, buyer=request.user.merchant.buyer)
    
    # Check if order can be cancelled (only pending orders can be cancelled)
    if order.status != 'pending':
        messages.error(request, 'Only pending orders can be cancelled.')
        return redirect('marketplace:order_detail', order_id=order.order_id)
    
    if request.method == 'POST':
        # Update order status
        order.status = 'cancelled'
        order.save()
        
        messages.success(request, 'Your order has been cancelled successfully.')
        return redirect('marketplace:my_orders')
    
    # If not POST, show confirmation page
    context = {
        'order': order,
    }
    
    return render(request, 'marketplace/cancel_order.html', context)