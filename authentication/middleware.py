from django.shortcuts import redirect


class RoleSelectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Skip for anonymous users or exempt paths
        exempt_paths = [
            '/select-role/',
            '/select-merchant-type/',
            '/setup-2fa/',
            '/verify-2fa/',
            '/logout/'
        ]
        
        if not request.user.is_authenticated or any(request.path.startswith(path) for path in exempt_paths):
            return response
            
        # Check 2FA first
        if request.user.is_authenticated and not request.user.is_2fa_enabled:
            return redirect('setup_2fa')
            
        # Then check roles
        if not hasattr(request.user, 'farmer') and not hasattr(request.user, 'merchant'):
            return redirect('select_role')
            
        return response