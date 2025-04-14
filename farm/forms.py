from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from .models import (
    Farm, FarmCondition, Field, Crop, ActivityLog, 
    PreparationLog, PlantingLog, MaintenanceLog, HarvestingLog
)

class FarmForm(forms.ModelForm):
    class Meta:
        model = Farm
        fields = ['name', 'location', 'size']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter farm name'
            }),
            'location': forms.TextInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter farm location'
            }),
            'size': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter farm size in hectares',
                'min': '0.01',
                'step': '0.01'
            })
        }
    
    def clean_name(self):
        """Sanitize and validate the name field"""
        name = self.cleaned_data.get('name')
        if name:
            # Strip whitespace from beginning and end
            name = name.strip()
            # Ensure name is not empty after stripping
            if not name:
                raise forms.ValidationError("Farm name cannot be empty")
        return name
        
    def clean_size(self):
        """Validate the size field"""
        size = self.cleaned_data.get('size')
        if size is not None and size <= 0:
            raise forms.ValidationError("Farm size must be positive")
        return size

class FarmConditionForm(forms.ModelForm):
    class Meta:
        model = FarmCondition
        fields = ['soil_ph', 'soil_moisture', 'rainfall', 'max_daily_temp', 'day_length']
        widgets = {
            'soil_ph': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter soil pH value (0-14)',
                'min': '0',
                'max': '14',
                'step': '0.1'
            }),
            'soil_moisture': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter soil moisture percentage (0-100)',
                'min': '0',
                'max': '100',
                'step': '0.1'
            }),
            'rainfall': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter rainfall in mm',
                'min': '0',
                'step': '0.1'
            }),
            'max_daily_temp': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter maximum daily temperature in °C',
                'min': '-50',
                'max': '60',
                'step': '0.1'
            }),
            'day_length': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter day length in hours (0-24)',
                'min': '0',
                'max': '24',
                'step': '0.1'
            })
        }
    
    def clean_soil_ph(self):
        """Validate the soil_ph field"""
        soil_ph = self.cleaned_data.get('soil_ph')
        if soil_ph is not None:
            if soil_ph < 0 or soil_ph > 14:
                raise forms.ValidationError("Soil pH must be between 0 and 14")
        return soil_ph
    
    def clean_soil_moisture(self):
        """Validate the soil_moisture field"""
        soil_moisture = self.cleaned_data.get('soil_moisture')
        if soil_moisture is not None:
            if soil_moisture < 0 or soil_moisture > 100:
                raise forms.ValidationError("Soil moisture must be between 0 and 100 percent")
        return soil_moisture
    
    def clean_rainfall(self):
        """Validate the rainfall field"""
        rainfall = self.cleaned_data.get('rainfall')
        if rainfall is not None and rainfall < 0:
            raise forms.ValidationError("Rainfall must be non-negative")
        return rainfall
    
    def clean_max_daily_temp(self):
        """Validate the max_daily_temp field"""
        max_daily_temp = self.cleaned_data.get('max_daily_temp')
        if max_daily_temp is not None:
            if max_daily_temp < -50 or max_daily_temp > 60:
                raise forms.ValidationError("Temperature must be between -50°C and 60°C")
        return max_daily_temp
    
    def clean_day_length(self):
        """Validate the day_length field"""
        day_length = self.cleaned_data.get('day_length')
        if day_length is not None:
            if day_length < 0 or day_length > 24:
                raise forms.ValidationError("Day length must be between 0 and 24 hours")
        return day_length

class FieldForm(forms.ModelForm):
    class Meta:
        model = Field
        fields = ['name', 'size', 'location_within_farm']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter field name'
            }),
            'size': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter field size in hectares',
                'min': '0.001',
                'step': '0.001'
            }),
            'location_within_farm': forms.TextInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter description of field location (e.g., "North corner", "Near the road")'
            })
        }
    
    def clean_name(self):
        """Sanitize and validate the name field"""
        name = self.cleaned_data.get('name')
        if name:
            # Strip whitespace from beginning and end
            name = name.strip()
            # Ensure name is not empty after stripping
            if not name:
                raise forms.ValidationError("Field name cannot be empty")
        return name
    
    def clean_size(self):
        """Validate the size field"""
        size = self.cleaned_data.get('size')
        if size is not None and size <= 0:
            raise forms.ValidationError("Field size must be positive")
        return size
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        size = cleaned_data.get('size')
        
        # Check if this is an update to an existing field
        if hasattr(self, 'instance') and self.instance.farm_id:
            farm = self.instance.farm
            # Check if field size is larger than farm size
            if size and size > farm.size:
                self.add_error('size', "Field size cannot be larger than farm size")
        
        return cleaned_data

class CropForm(forms.ModelForm):
    class Meta:
        model = Crop
        fields = ['crop_type', 'expected_harvest_date']
        widgets = {
            'crop_type': forms.TextInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter crop type'
            }),
            'expected_harvest_date': forms.DateInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'type': 'date',
                'required': False
            })
        }
    
    def clean_crop_type(self):
        """Sanitize and validate the crop_type field"""
        crop_type = self.cleaned_data.get('crop_type')
        if crop_type:
            # Strip whitespace from beginning and end
            crop_type = crop_type.strip()
            # Ensure crop_type is not empty after stripping
            if not crop_type:
                raise forms.ValidationError("Crop type cannot be empty")
        return crop_type
    
    def clean_expected_harvest_date(self):
        """Validate the expected_harvest_date field"""
        expected_harvest_date = self.cleaned_data.get('expected_harvest_date')
        planting_date = None
        
        # If this is an update to an existing crop, get the planting date
        if hasattr(self, 'instance') and self.instance.crop_id:
            planting_date = self.instance.planting_date
        
        if expected_harvest_date and planting_date and expected_harvest_date <= planting_date:
            raise forms.ValidationError("Expected harvest date must be after planting date")
        
        return expected_harvest_date

class ActivityLogForm(forms.ModelForm):
    class Meta:
        model = ActivityLog
        fields = ['activity_type', 'timestamp']
        widgets = {
            'activity_type': forms.Select(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
            }),
            'timestamp': forms.DateTimeInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'type': 'datetime-local',
                'max': timezone.now().strftime('%Y-%m-%dT%H:%M')
            })
        }
    
    def clean_timestamp(self):
        """Validate the timestamp field"""
        timestamp = self.cleaned_data.get('timestamp')
        if timestamp and timestamp > timezone.now():
            raise forms.ValidationError("Activity timestamp cannot be in the future")
        return timestamp

class PreparationLogForm(forms.ModelForm):
    field = forms.ModelChoiceField(
        queryset=Field.objects.none(),
        widget=forms.Select(attrs={
            'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
        })
    )
    
    class Meta:
        model = PreparationLog
        fields = ['field', 'equipment_used', 'desc']
        widgets = {
            'equipment_used': forms.TextInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter equipment used'
            }),
            'desc': forms.Textarea(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter description',
                'rows': 3
            })
        }
    
    def __init__(self, *args, **kwargs):
        farm = kwargs.pop('farm', None)
        super().__init__(*args, **kwargs)
        
        if farm:
            self.fields['field'].queryset = Field.objects.filter(farm=farm)
    
    def clean_equipment_used(self):
        """Sanitize and validate the equipment_used field"""
        equipment_used = self.cleaned_data.get('equipment_used')
        if equipment_used:
            # Strip whitespace from beginning and end
            equipment_used = equipment_used.strip()
            # Ensure equipment_used is not empty after stripping
            if not equipment_used:
                raise forms.ValidationError("Equipment used cannot be empty")
        return equipment_used
        
    def clean_desc(self):
        """Sanitize and validate the desc field"""
        desc = self.cleaned_data.get('desc')
        if desc:
            # Strip whitespace from beginning and end
            desc = desc.strip()
            # Ensure desc is not empty after stripping
            if not desc:
                raise forms.ValidationError("Description cannot be empty")
        return desc

class PlantingLogForm(forms.ModelForm):
    field = forms.ModelChoiceField(
        queryset=Field.objects.none(),
        widget=forms.Select(attrs={
            'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
        })
    )
    
    crop_type = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
            'placeholder': 'Enter crop type (e.g., Corn, Rice, Tomatoes)'
        })
    )
    
    expected_harvest_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
            'type': 'date'
        })
    )
    
    class Meta:
        model = PlantingLog
        fields = ['field', 'seed_quantity', 'seed_variety', 'fertilizer_applied', 'crop_type', 'expected_harvest_date']
        widgets = {
            'seed_quantity': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter seed quantity (kg)',
                'min': '0.01',
                'step': '0.01'
            }),
            'seed_variety': forms.TextInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter seed variety'
            }),
            'fertilizer_applied': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter fertilizer amount (kg)',
                'min': '0',
                'step': '0.01'
            })
        }
    
    def __init__(self, *args, **kwargs):
        farm = kwargs.pop('farm', None)
        super().__init__(*args, **kwargs)
        
        if farm:
            self.fields['field'].queryset = Field.objects.filter(farm=farm)
        
        # Ensure the selected field is kept when instance has a field
        if self.instance and hasattr(self.instance, 'field') and self.instance.field:
            # Get the field from the instance
            instance_field = self.instance.field
            
            # If the farm is different from the field's farm, adjust the queryset
            if farm and instance_field.farm != farm:
                # Make sure the field's farm is included in the queryset
                self.fields['field'].queryset = self.fields['field'].queryset | Field.objects.filter(pk=instance_field.pk)
            
            # Pre-select the field
            self.initial['field'] = instance_field.pk
    
    def clean_crop_type(self):
        """Sanitize and validate the crop_type field"""
        crop_type = self.cleaned_data.get('crop_type')
        if crop_type:
            # Strip whitespace from beginning and end
            crop_type = crop_type.strip()
            # Ensure crop_type is not empty after stripping
            if not crop_type:
                raise forms.ValidationError("Crop type cannot be empty")
            # Check for dangerous characters
            if any(char in crop_type for char in '<>{}[]\\/#'):
                raise forms.ValidationError("Crop type contains invalid characters")
        return crop_type
    
    def clean_seed_variety(self):
        """Sanitize and validate the seed_variety field"""
        seed_variety = self.cleaned_data.get('seed_variety')
        if seed_variety:
            # Strip whitespace from beginning and end
            seed_variety = seed_variety.strip()
            # Ensure seed_variety is not empty after stripping
            if not seed_variety:
                raise forms.ValidationError("Seed variety cannot be empty")
            # Check for dangerous characters
            if any(char in seed_variety for char in '<>{}[]\\/#'):
                raise forms.ValidationError("Seed variety contains invalid characters")
        return seed_variety
    
    def clean_seed_quantity(self):
        """Validate the seed_quantity field"""
        seed_quantity = self.cleaned_data.get('seed_quantity')
        if seed_quantity is not None:
            if seed_quantity <= 0:
                raise forms.ValidationError("Seed quantity must be positive")
            if seed_quantity > 10000:  # Reasonable upper limit for seed quantity in kg
                raise forms.ValidationError("Seed quantity seems too high")
        return seed_quantity
    
    def clean_fertilizer_applied(self):
        """Validate the fertilizer_applied field"""
        fertilizer_applied = self.cleaned_data.get('fertilizer_applied')
        if fertilizer_applied is not None:
            if fertilizer_applied < 0:
                raise forms.ValidationError("Fertilizer amount must be non-negative")
            if fertilizer_applied > 10000:  # Reasonable upper limit for fertilizer in kg
                raise forms.ValidationError("Fertilizer amount seems too high")
        return fertilizer_applied
    
    def clean_expected_harvest_date(self):
        """Validate the expected_harvest_date field"""
        expected_harvest_date = self.cleaned_data.get('expected_harvest_date')
        
        if expected_harvest_date:
            # Check if harvest date is in the past
            if expected_harvest_date < timezone.now().date():
                raise forms.ValidationError("Expected harvest date cannot be in the past")
                
            # Check if the date is too far in the future (e.g., more than 3 years)
            three_years_from_now = timezone.now().date() + timezone.timedelta(days=365*3)
            if expected_harvest_date > three_years_from_now:
                raise forms.ValidationError("Expected harvest date is too far in the future")
        
        return expected_harvest_date
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        
        # Get the values we need for validation
        activity_timestamp = None
        expected_harvest_date = cleaned_data.get('expected_harvest_date')
        
        # If this is an existing planting log, get the timestamp from the activity log
        if hasattr(self, 'instance') and self.instance.activity_log_id:
            activity_timestamp = self.instance.activity_log.timestamp
        
        # If we have both dates, make sure expected harvest date is after activity date
        if activity_timestamp and expected_harvest_date:
            if expected_harvest_date <= activity_timestamp.date():
                self.add_error('expected_harvest_date', 
                               "Expected harvest date must be after planting date")
        
        return cleaned_data


class MaintenanceLogForm(forms.ModelForm):
    crop = forms.ModelChoiceField(
        queryset=Crop.objects.none(),
        widget=forms.Select(attrs={
            'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
        })
    )
    
    class Meta:
        model = MaintenanceLog
        fields = ['crop', 'pesticide_applied', 'irrigation_amount', 'fertilizer_applied']
        widgets = {
            'pesticide_applied': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter pesticide amount (L)',
                'min': '0',
                'step': '0.01'
            }),
            'irrigation_amount': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter irrigation amount (L)',
                'min': '0',
                'step': '0.01'
            }),
            'fertilizer_applied': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter fertilizer amount (kg)',
                'min': '0',
                'step': '0.01'
            })
        }
    
    def __init__(self, *args, **kwargs):
        farm = kwargs.pop('farm', None)
        super().__init__(*args, **kwargs)
        
        if farm:
            # Only show non-harvested crops for maintenance
            self.fields['crop'].queryset = Crop.objects.filter(field__farm=farm, is_harvested=False)
    
    def clean_pesticide_applied(self):
        """Validate the pesticide_applied field"""
        pesticide_applied = self.cleaned_data.get('pesticide_applied')
        if pesticide_applied is not None:
            if pesticide_applied < 0:
                raise forms.ValidationError("Pesticide amount must be non-negative")
            if pesticide_applied > 1000:  # Reasonable upper limit for pesticide in liters
                raise forms.ValidationError("Pesticide amount seems too high")
        return pesticide_applied
    
    def clean_irrigation_amount(self):
        """Validate the irrigation_amount field"""
        irrigation_amount = self.cleaned_data.get('irrigation_amount')
        if irrigation_amount is not None:
            if irrigation_amount < 0:
                raise forms.ValidationError("Irrigation amount must be non-negative")
            if irrigation_amount > 100000:  # Reasonable upper limit for irrigation in liters
                raise forms.ValidationError("Irrigation amount seems too high")
        return irrigation_amount
    
    def clean_fertilizer_applied(self):
        """Validate the fertilizer_applied field"""
        fertilizer_applied = self.cleaned_data.get('fertilizer_applied')
        if fertilizer_applied is not None:
            if fertilizer_applied < 0:
                raise forms.ValidationError("Fertilizer amount must be non-negative")
            if fertilizer_applied > 10000:  # Reasonable upper limit for fertilizer in kg
                raise forms.ValidationError("Fertilizer amount seems too high")
        return fertilizer_applied
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        
        # Ensure at least one of the maintenance activities is provided
        pesticide_applied = cleaned_data.get('pesticide_applied')
        irrigation_amount = cleaned_data.get('irrigation_amount')
        fertilizer_applied = cleaned_data.get('fertilizer_applied')
        
        # If all values are None or 0, raise validation error
        if ((pesticide_applied is None or pesticide_applied == 0) and
            (irrigation_amount is None or irrigation_amount == 0) and
            (fertilizer_applied is None or fertilizer_applied == 0)):
            raise forms.ValidationError(
                "At least one maintenance activity (pesticide, irrigation, or fertilizer) must be provided"
            )
        
        return cleaned_data


class HarvestingLogForm(forms.ModelForm):
    crop = forms.ModelChoiceField(
        queryset=Crop.objects.none(),
        widget=forms.Select(attrs={
            'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
        })
    )
    
    class Meta:
        model = HarvestingLog
        fields = ['crop', 'yield_amount', 'harvest_quality']
        widgets = {
            'yield_amount': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter yield amount (kg)',
                'min': '0.01',
                'step': '0.01'
            }),
            'harvest_quality': forms.Select(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
            })
        }
    
    def __init__(self, *args, **kwargs):
        farm = kwargs.pop('farm', None)
        super().__init__(*args, **kwargs)
        
        if farm:
            # Only show non-harvested crops for harvesting
            self.fields['crop'].queryset = Crop.objects.filter(field__farm=farm, is_harvested=False)
    
    def clean_yield_amount(self):
        """Validate the yield_amount field"""
        yield_amount = self.cleaned_data.get('yield_amount')
        if yield_amount is not None:
            if yield_amount <= 0:
                raise forms.ValidationError("Yield amount must be positive")
            if yield_amount > 100000:  # Reasonable upper limit for yield in kg
                raise forms.ValidationError("Yield amount seems too high")
        return yield_amount
    
    def clean(self):
        """Additional validation for harvest date"""
        cleaned_data = super().clean()
        crop = cleaned_data.get('crop')
        
        if not crop:
            return cleaned_data
            
        # Get the current time from the form or context
        activity_timestamp = None
        if hasattr(self, 'instance') and hasattr(self.instance, 'activity_log') and self.instance.activity_log:
            activity_timestamp = self.instance.activity_log.timestamp
        elif 'activity_timestamp' in self.initial:
            activity_timestamp = self.initial.get('activity_timestamp')
            
        # Check if harvest date is valid relative to planting date
        if crop and activity_timestamp and activity_timestamp.date() < crop.planting_date:
            self.add_error(None, "Harvest date cannot be before planting date")
            
        # Check if the crop is mature enough to be harvested
        # This is a simple check that can be adjusted based on crop type
        if crop and activity_timestamp:
            days_since_planting = (activity_timestamp.date() - crop.planting_date).days
            if days_since_planting < 7:  # At least a week should pass before harvesting
                self.add_error(None, "Crop may be too young to harvest (less than 7 days since planting)")
                
        # If an expected harvest date was set, warn if harvesting is much earlier
        if crop and crop.expected_harvest_date and activity_timestamp:
            days_before_expected = (crop.expected_harvest_date - activity_timestamp.date()).days
            if days_before_expected > 30:  # If harvesting more than a month before expected
                self.add_error(None, "Harvesting significantly earlier than expected harvest date")
        
        return cleaned_data