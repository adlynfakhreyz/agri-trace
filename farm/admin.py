from django.contrib import admin
from .models import (
    Farm, FarmCondition, Field, Crop, ActivityLog, ActivityLogField,
    PreparationLog, PlantingLog, MaintenanceLog, HarvestingLog
)

class FarmConditionInline(admin.StackedInline):
    model = FarmCondition
    can_delete = False

class FieldInline(admin.TabularInline):
    model = Field
    extra = 0

@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'size', 'farmer', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'location', 'farmer__user__username')
    inlines = [FarmConditionInline, FieldInline]  # Use FieldInline instead of CropInline

class CropInline(admin.TabularInline):
    model = Crop
    extra = 0

@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ('name', 'farm', 'size', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'farm__name')
    inlines = [CropInline]  # Crops are now inlines for Fields

@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = ('crop_type', 'field', 'planting_date', 'expected_harvest_date', 'is_harvested')
    list_filter = ('planting_date', 'expected_harvest_date', 'is_harvested')
    search_fields = ('crop_type', 'field__name', 'field__farm__name')

class ActivityLogFieldInline(admin.TabularInline):
    model = ActivityLogField
    extra = 0

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('activity_type', 'farm', 'timestamp')
    list_filter = ('activity_type', 'timestamp')
    search_fields = ('farm__name',)
    inlines = [ActivityLogFieldInline]

@admin.register(PreparationLog)
class PreparationLogAdmin(admin.ModelAdmin):
    list_display = ('activity_log', 'field', 'equipment_used')

@admin.register(PlantingLog)
class PlantingLogAdmin(admin.ModelAdmin):
    list_display = ('activity_log', 'field', 'seed_variety', 'seed_quantity')

@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ('activity_log', 'crop', 'pesticide_applied', 'irrigation_amount', 'fertilizer_applied')

@admin.register(HarvestingLog)
class HarvestingLogAdmin(admin.ModelAdmin):
    list_display = ('activity_log', 'crop', 'yield_amount', 'harvest_quality')