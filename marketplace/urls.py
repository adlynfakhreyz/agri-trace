from django.urls import path
from . import views

app_name = 'marketplace'

urlpatterns = [
    # HomePage and user registration
    path('marketplace/', views.homepage, name='marketplace'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # Seller related
    path('become-seller/', views.become_seller, name='become_seller'),
    path('seller/dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('seller/products/add/', views.add_product, name='add_product'),
    path('seller/products/edit/<uuid:product_id>/', views.edit_product, name='edit_product'),
    path('seller/products/delete/<uuid:product_id>/', views.delete_product, name='delete_product'),
    path('seller/orders/', views.seller_orders, name='seller_orders'),
    path('seller/orders/<uuid:order_item_id>/', views.seller_order_detail, name='seller_order_detail'),
    path('seller/orders/update-status/<uuid:order_item_id>/', views.update_order_status, name='update_order_status'),
    
    # Products and browsing
    path('products/', views.product_list, name='product_list'),
    path('product/<uuid:product_id>/<slug:slug>/', views.product_detail, name='product_detail'),
    path('store/<int:seller_id>/', views.store_detail, name='store_detail'),
    
    # Cart
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<uuid:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<uuid:product_id>/', views.cart_remove, name='cart_remove'),
    
    # Checkout and Orders
    path('checkout/', views.checkout, name='checkout'),
    path('payment/<uuid:order_id>/', views.payment, name='payment'),
    path('orders/confirmation/<uuid:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('orders/', views.my_orders, name='my_orders'),
    path('orders/<uuid:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<uuid:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    
    # Reviews
    path('product/<uuid:product_id>/review/add/', views.add_product_review, name='add_product_review'),
    path('seller/<int:seller_id>/review/add/', views.add_seller_review, name='add_seller_review'),
    path('reviews/product/edit/<int:review_id>/', views.edit_product_review, name='edit_product_review'),
    path('reviews/seller/edit/<int:review_id>/', views.edit_seller_review, name='edit_seller_review'),
]