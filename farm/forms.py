from django import forms
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
                'step': '0.01'
            })
        }

class FarmConditionForm(forms.ModelForm):
    class Meta:
        model = FarmCondition
        fields = ['soil_ph', 'soil_moisture', 'rainfall', 'max_daily_temp', 'day_length']
        widgets = {
            'soil_ph': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter soil pH value',
                'step': '0.1'
            }),
            'soil_moisture': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter soil moisture percentage',
                'step': '0.1'
            }),
            'rainfall': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter rainfall in mm',
                'step': '0.1'
            }),
            'max_daily_temp': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter maximum daily temperature in °C',
                'step': '0.1'
            }),
            'day_length': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter day length in hours',
                'step': '0.1'
            })
        }

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
                'step': '0.01'
            }),
            'location_within_farm': forms.TextInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter description of field location (e.g., "North corner", "Near the road")'
            })
        }

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
                'type': 'datetime-local'
            })
        }

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
                'step': '0.01'
            }),
            'seed_variety': forms.TextInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter seed variety'
            }),
            'fertilizer_applied': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter fertilizer amount (kg)',
                'step': '0.01'
            })
        }
    
    def __init__(self, *args, **kwargs):
        farm = kwargs.pop('farm', None)
        super().__init__(*args, **kwargs)
        
        if farm:
            self.fields['field'].queryset = Field.objects.filter(farm=farm)

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
                'step': '0.01'
            }),
            'irrigation_amount': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter irrigation amount (L)',
                'step': '0.01'
            }),
            'fertilizer_applied': forms.NumberInput(attrs={
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm',
                'placeholder': 'Enter fertilizer amount (kg)',
                'step': '0.01'
            })
        }
    
    def __init__(self, *args, **kwargs):
        farm = kwargs.pop('farm', None)
        super().__init__(*args, **kwargs)
        
        if farm:
            # Only show non-harvested crops for maintenance
            self.fields['crop'].queryset = Crop.objects.filter(field__farm=farm, is_harvested=False)

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