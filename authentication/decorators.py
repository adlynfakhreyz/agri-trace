from django.shortcuts import redirect
from functools import wraps
from django.contrib import messages

def farmer_required(function):
    @wraps(function)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        
        if not hasattr(request.user, 'farmer'):
            messages.info(request, "You need to create a farm first to access this feature.")
            return redirect('farm:farm_create')
        
        return function(request, *args, **kwargs)
    return wrapper