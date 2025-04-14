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
        farmer, created = Farmer.objects.get_or_create(user=request.user)
    
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
    """View for displaying details of a specific farm with analytics"""
    # Get the farm or raise 404
    farm = get_object_or_404(Farm, farm_id=farm_id, farmer=request.user.farmer)
    
    # Get farm condition (or default values)
    try:
        farm_condition = farm.condition
    except FarmCondition.DoesNotExist:
        farm_condition = None
    
    # Get fields for this farm
    fields = farm.fields.all()
    
    # Get crops for this farm
    crops = Crop.objects.filter(field__farm=farm)
    active_crops = crops.filter(is_harvested=False)
    harvested_crops = crops.filter(is_harvested=True)
    
    # Get recent activities
    recent_activities = farm.activities.order_by('-timestamp')[:5]
    
    # Analytics: Activity counts by type
    from django.db.models import Count
    activity_counts = farm.activities.values('activity_type').annotate(count=Count('activity_type')).order_by('activity_type')
    
    # Create a dictionary with all activity types, setting count to 0 for types with no activities
    activity_types_dict = {activity_type: 0 for activity_type, _ in ActivityLog.ACTIVITY_CHOICES}
    for item in activity_counts:
        activity_types_dict[item['activity_type']] = item['count']
    
    # Analytics: Crop type distribution
    crop_type_counts = crops.values('crop_type').annotate(count=Count('crop_type')).order_by('-count')
    
    # Analytics: Yields from harvested crops
    from django.db.models import Sum, Avg
    harvest_stats = {}
    if harvested_crops.exists():
        harvest_logs = HarvestingLog.objects.filter(crop__in=harvested_crops)
        total_yield = harvest_logs.aggregate(total=Sum('yield_amount'))['total'] or 0
        avg_yield = harvest_logs.aggregate(avg=Avg('yield_amount'))['avg'] or 0
        harvest_stats = {
            'total_yield': total_yield,
            'avg_yield': avg_yield,
            'harvest_count': harvested_crops.count()
        }
    
    # Analytics: Field utilization
    field_stats = {}
    if fields.exists():
        total_field_area = fields.aggregate(total=Sum('size'))['total'] or 0
        if total_field_area > 0:
            # Calculate percentage of farm area being used for fields
            field_utilization = (total_field_area / farm.size) * 100 if farm.size > 0 else 0
            field_stats = {
                'total_area': total_field_area,
                'utilization': field_utilization,
                'count': fields.count()
            }
    
    # Analytics: Most recent activities per field
    field_latest_activities = []
    for field in fields:
        latest_activities = ActivityLog.objects.filter(
            farm=farm,
            preparationlog__field=field
        ).order_by('-timestamp')[:1]
        
        if latest_activities.exists():
            field_latest_activities.append({
                'field': field,
                'activity': latest_activities[0]
            })
    
    # Analytics: Activity trends over time (last 6 months)
    from django.utils import timezone
    import datetime
    
    end_date = timezone.now().date()
    start_date = end_date - datetime.timedelta(days=180)  # Last 6 months
    
    from django.db.models.functions import TruncMonth
    
    monthly_activities = farm.activities.filter(
        timestamp__date__gte=start_date,
        timestamp__date__lte=end_date
    ).annotate(
        month=TruncMonth('timestamp')
    ).values('month').annotate(
        count=Count('log_id')
    ).order_by('month')
    
    # Format for chart
    months = []
    counts = []
    for entry in monthly_activities:
        months.append(entry['month'].strftime('%b %Y'))
        counts.append(entry['count'])
    
    # Analytics: Calculate days since last maintenance for each active crop
    maintenance_status = []
    for crop in active_crops:
        maintenance_logs = MaintenanceLog.objects.filter(crop=crop).order_by('-activity_log__timestamp')
        if maintenance_logs.exists():
            last_maintenance = maintenance_logs[0].activity_log.timestamp.date()
            days_since_maintenance = (timezone.now().date() - last_maintenance).days
            maintenance_status.append({
                'crop': crop,
                'days_since_maintenance': days_since_maintenance,
                'last_maintenance_date': last_maintenance
            })
    
    # Organize analytics data
    analytics = {
        'activity_counts': activity_types_dict,
        'crop_type_counts': list(crop_type_counts),
        'harvest_stats': harvest_stats,
        'field_stats': field_stats,
        'field_latest_activities': field_latest_activities,
        'monthly_activity_data': {
            'months': months,
            'counts': counts
        },
        'maintenance_status': maintenance_status
    }
    
    return render(request, 'farm_detail.html', {
        'farm': farm,
        'farm_condition': farm_condition,
        'crops': crops,
        'active_crops': active_crops,
        'harvested_crops': harvested_crops,
        'recent_activities': recent_activities,
        'analytics': analytics
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

@login_required
def field_list(request, farm_id):
    """View for listing all fields of a farm"""
    farm = get_object_or_404(Farm, farm_id=farm_id, farmer=request.user.farmer)
    fields = farm.fields.all()
    
    return render(request, 'field_list.html', {
        'farm': farm,
        'fields': fields
    })

@login_required
def field_create(request, farm_id):
    """View for creating a new field"""
    farm = get_object_or_404(Farm, farm_id=farm_id, farmer=request.user.farmer)
    
    if request.method == 'POST':
        form = FieldForm(request.POST)
        if form.is_valid():
            field = form.save(commit=False)
            field.farm = farm
            
            # Manual validation for farm size before saving
            if field.size > farm.size:
                form.add_error('size', "Field size cannot be larger than farm size")
                return render(request, 'field_form.html', {
                    'form': form,
                    'farm': farm,
                    'action': 'Create'
                })
            
            try:
                field.save()
                messages.success(request, f"Field '{field.name}' was created successfully!")
                return redirect('farm:field_detail', farm_id=farm.farm_id, field_id=field.field_id)
            except Exception as e:
                form.add_error(None, f"Error saving field: {str(e)}")
    else:
        form = FieldForm()
    
    return render(request, 'field_form.html', {
        'form': form,
        'farm': farm,
        'action': 'Create'
    })
    
@login_required
def field_detail(request, farm_id, field_id):
    """View for displaying details of a specific field"""
    farm = get_object_or_404(Farm, farm_id=farm_id, farmer=request.user.farmer)
    field = get_object_or_404(Field, field_id=field_id, farm=farm)
    
    crops = field.crops.all()
    
    active_crops = field.get_active_crops()
    
    preparation_activities = field.preparation_activities.all().order_by('-activity_log__timestamp')
    
    planting_activities = field.planting_activities.all().order_by('-activity_log__timestamp')
    
    return render(request, 'field_detail.html', {
        'farm': farm,
        'field': field,
        'crops': crops,
        'active_crops': active_crops,
        'preparation_activities': preparation_activities,
        'planting_activities': planting_activities
    })

@login_required
def field_update(request, farm_id, field_id):
    """View for updating an existing field"""
    farm = get_object_or_404(Farm, farm_id=farm_id, farmer=request.user.farmer)
    field = get_object_or_404(Field, field_id=field_id, farm=farm)
    
    if request.method == 'POST':
        form = FieldForm(request.POST, instance=field)
        if form.is_valid():
            form.save()
            messages.success(request, f"Field '{field.name}' was updated successfully!")
            return redirect('farm:field_detail', farm_id=farm.farm_id, field_id=field.field_id)
    else:
        form = FieldForm(instance=field)
    
    return render(request, 'field_form.html', {
        'form': form,
        'farm': farm,
        'field': field,
        'action': 'Update'
    })

@login_required
def field_delete(request, farm_id, field_id):
    """View for deleting a field"""
    farm = get_object_or_404(Farm, farm_id=farm_id, farmer=request.user.farmer)
    field = get_object_or_404(Field, field_id=field_id, farm=farm)
    
    if request.method == 'POST':
        field_name = field.name
        field.delete()
        messages.success(request, f"Field '{field_name}' was deleted successfully!")
        return redirect('farm:field_list', farm_id=farm.farm_id)
    
    return render(request, 'field_confirm_delete.html', {
        'farm': farm,
        'field': field
    })
    
@login_required
def crop_detail(request, farm_id, crop_id):
    """View for displaying details of a specific crop"""
    farm = get_object_or_404(Farm, farm_id=farm_id, farmer=request.user.farmer)
    crop = get_object_or_404(Crop, crop_id=crop_id, field__farm=farm)
    
    # Get the planting activity
    planting_activity = crop.planting_activity
    
    # Get maintenance activities
    maintenance_activities = crop.maintenance_activities.all().order_by('-activity_log__timestamp')
    
    # Get harvest activity if exists
    try:
        harvest_activity = crop.harvest_activity
    except HarvestingLog.DoesNotExist:
        harvest_activity = None
    
    return render(request, 'crop_detail.html', {
        'farm': farm,
        'crop': crop,
        'field': crop.field,
        'planting_activity': planting_activity,
        'maintenance_activities': maintenance_activities,
        'harvest_activity': harvest_activity
    })
    
@login_required
def activity_log_list(request, farm_id):
    """View for listing all activity logs for a specific farm"""
    # Get the farm or raise 404
    farm = get_object_or_404(Farm, farm_id=farm_id, farmer=request.user.farmer)
    
    # Get all activities for this farm, newest first
    activities = farm.activities.all().order_by('-timestamp')
    
    # Filter by activity type if specified
    activity_type = request.GET.get('type')
    if activity_type:
        activities = activities.filter(activity_type=activity_type)
    
    return render(request, 'activity_log_list.html', {
        'farm': farm,
        'activities': activities,
        'activity_type': activity_type
    })

@login_required
@transaction.atomic
def activity_log_create(request, farm_id):
    """View for creating a new activity log with the updated workflow"""
    farm = get_object_or_404(Farm, farm_id=farm_id, farmer=request.user.farmer)
    
    if request.method == 'POST':
        activity_form = ActivityLogForm(request.POST)
        activity_type = request.POST.get('activity_type')
        
        # Determine which specialized form to use based on activity type
        specialized_form = None
        
        if activity_type == 'preparation':
            specialized_form = PreparationLogForm(request.POST, farm=farm)
        elif activity_type == 'planting':
            specialized_form = PlantingLogForm(request.POST, farm=farm)
        elif activity_type == 'maintenance':
            specialized_form = MaintenanceLogForm(request.POST, farm=farm)
        elif activity_type == 'harvesting':
            specialized_form = HarvestingLogForm(request.POST, farm=farm)
        
        if activity_form.is_valid() and (specialized_form is None or specialized_form.is_valid()):
            # Create activity log
            activity = activity_form.save(commit=False)
            activity.farm = farm
            activity.save()
            
            # Create specialized log based on activity type
            if activity_type == 'preparation':
                preparation_log = specialized_form.save(commit=False)
                preparation_log.activity_log = activity
                preparation_log.save()
                
                messages.success(request, "Land preparation activity logged successfully!")
                
            elif activity_type == 'planting':
                # Create planting log
                planting_log = specialized_form.save(commit=False)
                planting_log.activity_log = activity
                planting_log.save()
                
                # Create a new crop associated with this planting activity
                field = specialized_form.cleaned_data['field']
                crop_type = specialized_form.cleaned_data['crop_type']
                expected_harvest_date = specialized_form.cleaned_data['expected_harvest_date']
                seed_variety = specialized_form.cleaned_data['seed_variety']
                
                # Create crop instance
                crop = Crop.objects.create(
                    field=field,
                    crop_type=crop_type,
                    planting_date=activity.timestamp.date(),
                    expected_harvest_date=expected_harvest_date,
                    seed_variety=seed_variety,
                    planting_activity=planting_log
                )
                
                messages.success(request, f"Planting activity logged successfully! A new {crop_type} crop has been added.")
                
            elif activity_type == 'maintenance':
                maintenance_log = specialized_form.save(commit=False)
                maintenance_log.activity_log = activity
                maintenance_log.save()
                
                crop = specialized_form.cleaned_data['crop']
                messages.success(request, f"Maintenance activity for {crop.crop_type} logged successfully!")
                
            elif activity_type == 'harvesting':
                harvesting_log = specialized_form.save(commit=False)
                harvesting_log.activity_log = activity
                harvesting_log.save()
                
                # The crop will be automatically marked as harvested by the save method of HarvestingLog
                crop = specialized_form.cleaned_data['crop']
                messages.success(request, f"Harvesting activity for {crop.crop_type} logged successfully! The crop has been marked as harvested.")
            
            return redirect('farm:activity_log_detail', farm_id=farm.farm_id, log_id=activity.log_id)
    else:
        activity_form = ActivityLogForm(initial={'timestamp': timezone.now()})
        specialized_form = None
    
    # Check if farm has any fields for preparation or planting activities
    has_fields = farm.fields.exists()
    
    # Check if farm has any active crops for maintenance and harvesting
    has_active_crops = Crop.objects.filter(field__farm=farm, is_harvested=False).exists()
    
    return render(request, 'activity_log_form.html', {
        'farm': farm,
        'activity_form': activity_form,
        'specialized_form': specialized_form,
        'action': 'Create',
        'has_fields': has_fields,
        'has_active_crops': has_active_crops
    })
    
@login_required
def activity_log_detail(request, farm_id, log_id):
    """View for displaying details of a specific activity log"""
    # Get the farm or raise 404
    farm = get_object_or_404(Farm, farm_id=farm_id, farmer=request.user.farmer)
    
    # Get the activity log or raise 404
    activity = get_object_or_404(ActivityLog, log_id=log_id, farm=farm)
    
    # Get the specific type of log if it exists
    specialized_log = None
    if activity.activity_type == 'preparation':
        try:
            specialized_log = activity.preparationlog
        except PreparationLog.DoesNotExist:
            pass
    elif activity.activity_type == 'planting':
        try:
            specialized_log = activity.plantinglog
        except PlantingLog.DoesNotExist:
            pass
    elif activity.activity_type == 'maintenance':
        try:
            specialized_log = activity.maintenancelog
        except MaintenanceLog.DoesNotExist:
            pass
    elif activity.activity_type == 'harvesting':
        try:
            specialized_log = activity.harvestinglog
        except HarvestingLog.DoesNotExist:
            pass
    
    # Get all custom fields for this activity
    fields = activity.fields.all()
    
    return render(request, 'activity_log_detail.html', {
        'farm': farm,
        'activity': activity,
        'specialized_log': specialized_log,
        'fields': fields
    })

@login_required
@transaction.atomic
def activity_log_update(request, farm_id, log_id):
    """View for updating an existing activity log"""
    farm = get_object_or_404(Farm, farm_id=farm_id, farmer=request.user.farmer)
    activity = get_object_or_404(ActivityLog, log_id=log_id, farm=farm)
    
    # Get the specialized log instance if it exists
    specialized_log = None
    specialized_form = None
    
    if activity.activity_type == 'preparation':
        try:
            specialized_log = activity.preparationlog
            specialized_form = PreparationLogForm(instance=specialized_log, farm=farm)
        except PreparationLog.DoesNotExist:
            pass
    elif activity.activity_type == 'planting':
        try:
            specialized_log = activity.plantinglog
            specialized_form = PlantingLogForm(instance=specialized_log, farm=farm)
            
            # Pre-fill crop fields if this planting activity has a crop
            try:
                crop = specialized_log.crop
                initial_data = {
                    'crop_type': crop.crop_type,
                    'expected_harvest_date': crop.expected_harvest_date
                }
                specialized_form = PlantingLogForm(
                    instance=specialized_log, 
                    farm=farm, 
                    initial=initial_data
                )
            except Crop.DoesNotExist:
                pass
                
        except PlantingLog.DoesNotExist:
            pass
    elif activity.activity_type == 'maintenance':
        try:
            specialized_log = activity.maintenancelog
            specialized_form = MaintenanceLogForm(instance=specialized_log, farm=farm)
        except MaintenanceLog.DoesNotExist:
            pass
    elif activity.activity_type == 'harvesting':
        try:
            specialized_log = activity.harvestinglog
            specialized_form = HarvestingLogForm(instance=specialized_log, farm=farm)
        except HarvestingLog.DoesNotExist:
            pass
    
    if request.method == 'POST':
        activity_form = ActivityLogForm(request.POST, instance=activity)
        
        # Handle specialized form if it exists
        if specialized_log:
            if activity.activity_type == 'preparation':
                specialized_form = PreparationLogForm(request.POST, instance=specialized_log, farm=farm)
            elif activity.activity_type == 'planting':
                specialized_form = PlantingLogForm(request.POST, instance=specialized_log, farm=farm)
            elif activity.activity_type == 'maintenance':
                specialized_form = MaintenanceLogForm(request.POST, instance=specialized_log, farm=farm)
            elif activity.activity_type == 'harvesting':
                specialized_form = HarvestingLogForm(request.POST, instance=specialized_log, farm=farm)
        
        if activity_form.is_valid() and (specialized_form is None or specialized_form.is_valid()):
            activity = activity_form.save()
            
            if specialized_form:
                specialized_log = specialized_form.save()
                
                # Update associated crop if this is a planting activity
                if activity.activity_type == 'planting':
                    try:
                        crop = specialized_log.crop
                        crop.crop_type = specialized_form.cleaned_data.get('crop_type', crop.crop_type)
                        crop.expected_harvest_date = specialized_form.cleaned_data.get('expected_harvest_date', crop.expected_harvest_date)
                        crop.seed_variety = specialized_log.seed_variety
                        crop.save()
                    except Crop.DoesNotExist:
                        # Create a new crop if one doesn't exist
                        field = specialized_form.cleaned_data['field']
                        crop_type = specialized_form.cleaned_data['crop_type']
                        expected_harvest_date = specialized_form.cleaned_data['expected_harvest_date']
                        
                        crop = Crop.objects.create(
                            field=field,
                            crop_type=crop_type,
                            planting_date=activity.timestamp.date(),
                            expected_harvest_date=expected_harvest_date,
                            seed_variety=specialized_log.seed_variety,
                            planting_activity=specialized_log
                        )
            
            messages.success(request, "Activity log updated successfully!")
            return redirect('farm:activity_log_detail', farm_id=farm.farm_id, log_id=activity.log_id)
    else:
        activity_form = ActivityLogForm(instance=activity)
    
    # Set read-only for activity type (shouldn't change activity type on update)
    activity_form.fields['activity_type'].widget.attrs['disabled'] = True
    
    return render(request, 'activity_log_form.html', {
        'farm': farm,
        'activity': activity,
        'activity_form': activity_form,
        'specialized_form': specialized_form,
        'action': 'Update'
    })
    
@login_required
def activity_log_delete(request, farm_id, log_id):
    """View for deleting an activity log"""
    # Get the farm or raise 404
    farm = get_object_or_404(Farm, farm_id=farm_id, farmer=request.user.farmer)
    
    # Get the activity log or raise 404
    activity = get_object_or_404(ActivityLog, log_id=log_id, farm=farm)
    
    if request.method == 'POST':
        # Handle each specific type of activity log
        activity_type = activity.activity_type
        
        if activity_type == 'planting':
            # If this is a planting activity, we need to check if it has a crop associated
            try:
                crop = activity.plantinglog.crop
                # If the crop has maintenance or harvesting activities, prevent deletion
                if crop.maintenance_activities.exists() or hasattr(crop, 'harvest_activity'):
                    messages.error(request, "Cannot delete this planting activity because it has dependent maintenance or harvesting activities. Delete those first.")
                    return redirect('farm:activity_log_detail', farm_id=farm.farm_id, log_id=activity.log_id)
                
                # Otherwise, delete the crop first
                crop.delete()
            except (PlantingLog.DoesNotExist, Crop.DoesNotExist, AttributeError):
                # If there's no plantinglog or associated crop, just continue
                pass
                
        elif activity_type == 'harvesting':
            # If this is a harvesting activity, we need to un-mark the crop as harvested
            try:
                crop = activity.harvestinglog.crop
                crop.is_harvested = False
                crop.harvest_date = None
                crop.save()
            except (HarvestingLog.DoesNotExist, Crop.DoesNotExist, AttributeError):
                # If there's no harvestinglog or associated crop, just continue
                pass
        
        # Now delete the activity log (this will cascade delete the specialized logs)
        activity_type_display = activity.get_activity_type_display()
        activity.delete()
        
        messages.success(request, f"{activity_type_display} activity deleted successfully!")
        return redirect('farm:activity_log_list', farm_id=farm.farm_id)
    
    return render(request, 'activity_log_confirm_delete.html', {
        'farm': farm,
        'activity': activity
    })

@login_required
def get_specialized_form(request, farm_id):
    """AJAX view to get the specialized form based on activity type"""
    farm = get_object_or_404(Farm, farm_id=farm_id, farmer=request.user.farmer)
    activity_type = request.GET.get('activity_type')
    
    if not activity_type:
        return JsonResponse({'error': 'Activity type is required'}, status=400)
    
    # Render the appropriate form template
    if activity_type == 'preparation':
        form = PreparationLogForm(farm=farm)
        template = 'partials/preparation_form.html'
    elif activity_type == 'planting':
        form = PlantingLogForm(farm=farm)
        template = 'partials/planting_form.html'
    elif activity_type == 'maintenance':
        form = MaintenanceLogForm(farm=farm)
        template = 'partials/maintenance_form.html'
    elif activity_type == 'harvesting':
        form = HarvestingLogForm(farm=farm)
        template = 'partials/harvesting_form.html'
    else:
        return JsonResponse({'html': ''})  # No specialized form for this type
    
    html = render(request, template, {'form': form}).content.decode('utf-8')
    return JsonResponse({'html': html})

@login_required
def get_active_crops(request, farm_id):
    """AJAX view to get active crops for a farm"""
    farm = get_object_or_404(Farm, farm_id=farm_id, farmer=request.user.farmer)
    field_id = request.GET.get('field_id')
    
    crops = Crop.objects.filter(field__farm=farm, is_harvested=False)
    
    if field_id:
        crops = crops.filter(field_id=field_id)
    
    crops_data = [{'id': str(crop.crop_id), 'name': f"{crop.crop_type} - {crop.field.name}"} for crop in crops]
    
    return JsonResponse({'crops': crops_data})