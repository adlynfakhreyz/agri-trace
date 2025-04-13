from django.db import models
from authentication.models import Farmer
import uuid
from django.utils import timezone

class Farm(models.Model):
    farm_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    size = models.FloatField(help_text="Farm size in hectares")
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='farms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def get_farm_id(self):
        return self.farm_id
    
    def get_farm_name(self):
        return self.name
    
    def get_farm_location(self):
        return self.location
    
    def add_farm_activity(self, activity_type, string_value=None, date_value=None):
        """Add an activity to the farm"""
        activity = ActivityLog.objects.create(
            farm=self,
            activity_type=activity_type,
            timestamp=date_value or timezone.now()
        )
        return activity
    
    def get_crop_count(self):
        """Get the count of crops associated with this farm"""
        return self.crops.count()

    def get_field_count(self):
        """Get the count of fields associated with this farm"""
        return self.fields.count()

class FarmCondition(models.Model):
    farm = models.OneToOneField(Farm, on_delete=models.CASCADE, related_name='condition')
    soil_ph = models.FloatField(null=True, blank=True)
    soil_moisture = models.FloatField(null=True, blank=True)
    rainfall = models.FloatField(null=True, blank=True)
    max_daily_temp = models.FloatField(null=True, blank=True)
    day_length = models.FloatField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Conditions for {self.farm.name}"
    
    def get_ph(self):
        return self.soil_ph
    
    def get_soil_moisture(self):
        return self.soil_moisture
    
    def get_rainfall(self):
        return self.rainfall
    
    def get_max_daily_temp(self):
        return self.max_daily_temp
    
    def get_day_length(self):
        return self.day_length

class Field(models.Model):
    """Represents a specific field within a farm"""
    field_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='fields')
    name = models.CharField(max_length=100)
    size = models.FloatField(help_text="Field size in hectares")
    location_within_farm = models.CharField(max_length=255, help_text="Description of field location within the farm", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} at {self.farm.name}"
    
    def get_id(self):
        return self.field_id
    
    def get_active_crops(self):
        """Get crops that are currently active (not harvested) on this field"""
        return self.crops.filter(is_harvested=False)
    
    def get_crop_count(self):
        """Get the count of all crops planted on this field"""
        return self.crops.count()
    
    def get_active_crop_count(self):
        """Get the count of active crops on this field"""
        return self.get_active_crops().count()

class Crop(models.Model):
    crop_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='crops', null=True, blank=True)
    crop_type = models.CharField(max_length=100)
    planting_date = models.DateField()
    expected_harvest_date = models.DateField(null=True, blank=True)
    is_harvested = models.BooleanField(default=False)
    harvest_date = models.DateField(null=True, blank=True)
    seed_variety = models.CharField(max_length=100, blank=True, null=True)
    planting_activity = models.OneToOneField('PlantingLog', on_delete=models.SET_NULL, null=True, related_name='crop')
    
    def __str__(self):
        return f"{self.crop_type} at {self.field.name} ({self.field.farm.name})"
    
    def get_id(self):
        return self.crop_id
    
    def get_crop_type(self):
        return self.crop_type
    
    def get_farm(self):
        """Get the farm this crop belongs to"""
        return self.field.farm
    
    def get_maintenance_activities(self):
        """Get all maintenance activities for this crop"""
        return self.maintenance_activities.all().order_by('-activity_log__timestamp')
    
    def get_harvest_activity(self):
        """Get the harvest activity for this crop if exists"""
        try:
            return self.harvest_activity
        except HarvestingLog.DoesNotExist:
            return None
    
    def mark_as_harvested(self, harvest_date=None):
        """Mark this crop as harvested"""
        self.is_harvested = True
        self.harvest_date = harvest_date or timezone.now().date()
        self.save()

class ActivityLog(models.Model):
    ACTIVITY_CHOICES = [
        ('planting', 'Planting'),
        ('maintenance', 'Maintenance'),
        ('harvesting', 'Harvesting'),
        ('preparation', 'Land Preparation'),
        ('other', 'Other')
    ]
    
    log_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_CHOICES)
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.activity_type} on {self.farm.name} at {self.timestamp}"
    
    def get_log_id(self):
        return self.log_id
    
    def get_activity_type(self):
        return self.activity_type
    
    def get_timestamp(self):
        return self.timestamp
    
    def get_activity_type_choices(self):
        """Return the choices for the activity_type field"""
        return self.ACTIVITY_CHOICES

class ActivityLogField(models.Model):
    field_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    field_name = models.CharField(max_length=100)
    field_value = models.TextField()
    activity_log = models.ForeignKey(ActivityLog, on_delete=models.CASCADE, related_name='fields')
    
    def __str__(self):
        return f"{self.field_name}: {self.field_value}"
    
    def get_id(self):
        return self.field_id
    
    def get_field_name(self):
        return self.field_name
    
    def get_field_value(self):
        return self.field_value

# Specialized Activity Log types
class PreparationLog(models.Model):
    activity_log = models.OneToOneField(ActivityLog, on_delete=models.CASCADE, primary_key=True)
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='preparation_activities', null=True, blank=True)
    equipment_used = models.CharField(max_length=255)
    desc = models.TextField()
    
    def get_equipment_used(self):
        return self.equipment_used
    
    def get_desc(self):
        return self.desc
    
    def set_equipment_used(self, equipment_used):
        self.equipment_used = equipment_used
        self.save()
    
    def set_desc(self, desc):
        self.desc = desc
        self.save()

class PlantingLog(models.Model):
    activity_log = models.OneToOneField(ActivityLog, on_delete=models.CASCADE, primary_key=True)
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='planting_activities', null=True, blank=True)
    seed_quantity = models.FloatField()
    seed_variety = models.CharField(max_length=255)
    fertilizer_applied = models.FloatField()
    
    def get_seed_quantity(self):
        return self.seed_quantity
    
    def get_seed_variety(self):
        return self.seed_variety
    
    def get_fertilizer_applied(self):
        return self.fertilizer_applied
    
    def set_seed_quantity(self, quantity):
        self.seed_quantity = quantity
        self.save()
    
    def set_seed_variety(self, variety):
        self.seed_variety = variety
        self.save()
    
    def set_fertilizer_applied(self, fertilizer_applied):
        self.fertilizer_applied = fertilizer_applied
        self.save()

class MaintenanceLog(models.Model):
    activity_log = models.OneToOneField(ActivityLog, on_delete=models.CASCADE, primary_key=True)
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='maintenance_activities', null=True, blank=True)
    pesticide_applied = models.FloatField(null=True, blank=True)
    irrigation_amount = models.FloatField(null=True, blank=True)
    fertilizer_applied = models.FloatField(null=True, blank=True)
    
    def get_pesticide_applied(self):
        return self.pesticide_applied
    
    def get_irrigation_amount(self):
        return self.irrigation_amount
    
    def get_fertilizer_applied(self):
        return self.fertilizer_applied
    
    def set_pesticide_applied(self, amount):
        self.pesticide_applied = amount
        self.save()
    
    def set_irrigation_amount(self, amount):
        self.irrigation_amount = amount
        self.save()
    
    def set_fertilizer_applied(self, amount):
        self.fertilizer_applied = amount
        self.save()

class HarvestingLog(models.Model):
    activity_log = models.OneToOneField(ActivityLog, on_delete=models.CASCADE, primary_key=True)
    crop = models.OneToOneField(Crop, on_delete=models.CASCADE, related_name='harvest_activity', null=True, blank=True)
    yield_amount = models.FloatField()
    harvest_quality = models.IntegerField(choices=[(1, 'Poor'), (2, 'Fair'), (3, 'Good'), (4, 'Excellent')])
    
    def get_yield_amount(self):
        return self.yield_amount
    
    def get_harvest_quality(self):
        return self.harvest_quality
    
    def set_yield_amount(self, amount):
        self.yield_amount = amount
        self.save()
    
    def set_harvest_quality(self, quality):
        self.harvest_quality = quality
        self.save()
    
    def save(self, *args, **kwargs):
        # Mark the crop as harvested when saving a harvest log
        super().save(*args, **kwargs)
        if not self.crop.is_harvested:
            self.crop.mark_as_harvested(harvest_date=self.activity_log.timestamp.date())