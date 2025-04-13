from django.db.models import Count
from authentication.models import Farmer

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.views.generic import ListView
from django.http import JsonResponse
from .models import (
    Farm, FarmCondition, Field, Crop, ActivityLog, 
    PreparationLog, PlantingLog, MaintenanceLog, HarvestingLog
)
from .forms import (
    FarmForm, FarmConditionForm, FieldForm, CropForm,
    ActivityLogForm, PreparationLogForm, PlantingLogForm, 
    MaintenanceLogForm, HarvestingLogForm
)

@login_required
def farm_list(request):
    """View for listing all farms owned by the current user's farmer profile"""
    # Check if user has a farmer profile
    if not hasattr(request.user, 'farmer'):
        messages.warning(request, "You need to set up a farmer profile first.")
        # Redirect to select role page (assuming it exists)
        return redirect('select_role')
    
    farms = Farm.objects.filter(farmer=request.user.farmer)
    farm_count = farms.count()
    
    # Get crop counts for each farm
    farms_with_counts = farms.annotate(crop_count=Count('fields__crops'))
    
    return render(request, 'farm_list.html', {
        'farms': farms_with_counts,
        'farm_count': farm_count
    })

@login_required
@transaction.atomic
def farm_create(request):
    """View for creating a new farm"""
    # Check if user has a farmer profile
    if not hasattr(request.user, 'farmer'):
        try:
            # Try to create a farmer profile if it doesn't exist
            farmer = Farmer.objects.create(user=request.user)
        except Exception as e:
            messages.error(request, f"Failed to create farmer profile: {str(e)}")
            return redirect('home')
    
    if request.method == 'POST':
        form = FarmForm(request.POST)
        if form.is_valid():
            # Create farm but don't save to DB yet
            farm = form.save(commit=False)
            farm.farmer = request.user.farmer
            farm.save()
            
            # Create default farm condition
            FarmCondition.objects.create(farm=farm)
            
            messages.success(request, f"Farm '{farm.name}' was created successfully!")
            return redirect('farm:farm_detail', farm_id=farm.farm_id)
    else:
        form = FarmForm()
    
    return render(request, 'farm_form.html', {
        'form': form,
        'action': 'Create'
    })

@login_required
def farm_detail(request, farm_id):
    """View for displaying details of a specific farm"""
    # Get the farm or raise 404
    farm = get_object_or_404(Farm, farm_id=farm_id, farmer=request.user.farmer)
    
    # Get farm condition (or default values)
    try:
        farm_condition = farm.condition
    except FarmCondition.DoesNotExist:
        farm_condition = None
    
    # Get crops for this farm
    crops = Crop.objects.filter(field__farm=farm)
    
    # Get recent activities
    recent_activities = farm.activities.order_by('-timestamp')[:5]
    
    return render(request, 'farm_detail.html', {
        'farm': farm,
        'farm_condition': farm_condition,
        'crops': crops,
        'recent_activities': recent_activities
    })

@login_required
def farm_update(request, farm_id):
    """View for updating an existing farm"""
    # Get the farm or raise 404
    farm = get_object_or_404(Farm, farm_id=farm_id, farmer=request.user.farmer)
    
    if request.method == 'POST':
        form = FarmForm(request.POST, instance=farm)
        if form.is_valid():
            form.save()
            messages.success(request, f"Farm '{farm.name}' was updated successfully!")
            return redirect('farm:farm_detail', farm_id=farm.farm_id)
    else:
        form = FarmForm(instance=farm)
    
    return render(request, 'farm_form.html', {
        'form': form,
        'farm': farm,
        'action': 'Update'
    })

@login_required
def farm_delete(request, farm_id):
    """View for deleting a farm"""
    # Get the farm or raise 404
    farm = get_object_or_404(Farm, farm_id=farm_id, farmer=request.user.farmer)
    
    if request.method == 'POST':
        farm_name = farm.name
        farm.delete()
        messages.success(request, f"Farm '{farm_name}' was deleted successfully!")
        return redirect('farm:farm_list')
    
    return render(request, 'farm_confirm_delete.html', {'farm': farm})

@login_required
def farm_condition_update(request, farm_id):
    """View for updating farm conditions"""
    # Get the farm or raise 404
    farm = get_object_or_404(Farm, farm_id=farm_id, farmer=request.user.farmer)
    
    # Get or create farm condition
    farm_condition, created = FarmCondition.objects.get_or_create(farm=farm)
    
    if request.method == 'POST':
        form = FarmConditionForm(request.POST, instance=farm_condition)
        if form.is_valid():
            form.save()
            messages.success(request, "Farm conditions updated successfully!")
            return redirect('farm:farm_detail', farm_id=farm.farm_id)
    else:
        form = FarmConditionForm(instance=farm_condition)
    
    return render(request, 'farm_condition_form.html', {
        'form': form,
        'farm': farm
    })

