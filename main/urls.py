from main import views
from django.urls import path
from .views import home_view

urlpatterns = [
    path('', home_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('toggle-drawer/', views.toggle_drawer, name='toggle_drawer'),
]