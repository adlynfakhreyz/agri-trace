from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required

from farm.models import ActivityLog, Crop, Farm
# Create your views here.

def home_view(request):
    return render(request, 'home.html')

@login_required
def dashboard_view(request):
    """Dashboard view showing farms overview"""
    # Check if user has a farmer profile
    if not hasattr(request.user, 'farmer'):
        messages.warning(request, "You need to set up a farmer profile first.")
        return redirect('select_role')
    
    farms = Farm.objects.filter(farmer=request.user.farmer)
    farm_count = farms.count()
    
    if farm_count == 0:
        # If no farms, suggest creating one
        return render(request, 'dashboard.html', {
            'farm_count': 0,
            'has_farms': False
        })
    
    # Get total crops 
    total_crops = Crop.objects.filter(field__farm__in=farms).count()
    
    # Get some recent activities
    recent_activities = ActivityLog.objects.filter(
        farm__farmer=request.user.farmer
    ).order_by('-timestamp')[:5]
    
    return render(request, 'dashboard.html', {
        'farms': farms,
        'farm_count': farm_count,
        'total_crops': total_crops,
        'recent_activities': recent_activities,
        'has_farms': True
    })

def about_us_view(request):
    return render(request, 'about_us.html')

def contact_view(request):
    return render(request, 'contact.html')

from django.http import JsonResponse

@login_required
def toggle_drawer(request):
    if request.method == 'POST':
        collapsed = request.POST.get('collapsed') == 'true'
        request.session['drawer_collapsed'] = collapsed
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=400)    