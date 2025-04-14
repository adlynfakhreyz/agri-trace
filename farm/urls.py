from django.urls import path
from . import views

app_name = 'farm'

urlpatterns = [
    path('farms/', views.farm_list, name='farm_list'),
    path('farms/create/', views.farm_create, name='farm_create'),
    path('farms/<uuid:farm_id>/', views.farm_detail, name='farm_detail'),
    path('farms/<uuid:farm_id>/update/', views.farm_update, name='farm_update'),
    path('farms/<uuid:farm_id>/delete/', views.farm_delete, name='farm_delete'),
    path('farms/<uuid:farm_id>/conditions/', views.farm_condition_update, name='farm_condition_update'),
    
    path('farms/<uuid:farm_id>/fields/', views.field_list, name='field_list'),
    path('farms/<uuid:farm_id>/fields/create/', views.field_create, name='field_create'),
    path('farms/<uuid:farm_id>/fields/<uuid:field_id>/', views.field_detail, name='field_detail'),
    path('farms/<uuid:farm_id>/fields/<uuid:field_id>/update/', views.field_update, name='field_update'),
    path('farms/<uuid:farm_id>/fields/<uuid:field_id>/delete/', views.field_delete, name='field_delete'),
    
    path('farms/<uuid:farm_id>/crops/<uuid:crop_id>/', views.crop_detail, name='crop_detail'),
    
    path('farms/<uuid:farm_id>/activities/', views.activity_log_list, name='activity_log_list'),
    path('farms/<uuid:farm_id>/activities/create/', views.activity_log_create, name='activity_log_create'),
    path('farms/<uuid:farm_id>/activities/<uuid:log_id>/', views.activity_log_detail, name='activity_log_detail'),
    path('farms/<uuid:farm_id>/activities/<uuid:log_id>/update/', views.activity_log_update, name='activity_log_update'),
    path('farms/<uuid:farm_id>/activities/<uuid:log_id>/delete/', views.activity_log_delete, name='activity_log_delete'),
    
    path('farms/<uuid:farm_id>/get-specialized-form/', views.get_specialized_form, name='get_specialized_form'),
    path('farms/<uuid:farm_id>/get-active-crops/', views.get_active_crops, name='get_active_crops'),

    path('farms/<uuid:farm_id>/crops/<uuid:crop_id>/predict-harvest/', views.crop_harvest_prediction, name='crop_harvest_prediction'),

    path('farms/<uuid:farm_id>/export-pdf/', views.export_farm_pdf, name='export_farm_pdf'),
]