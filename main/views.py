from django.shortcuts import render
from django.contrib.auth.decorators import login_required
# Create your views here.

def home_view(request):
    return render(request, 'home.html')

def dashboard_view(request):
    return render(request, 'dashboard.html')

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