from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Check if user needs to change password
            if request.user.last_login is None and 'force_password_change' not in request.path:
                # Exclude certain URLs from the redirect
                excluded_paths = [
                    reverse('accounts:force_password_change'),
                    reverse('account_logout'),
                    '/static/',
                    '/media/',
                ]
                
                if not any(request.path.startswith(path) for path in excluded_paths):
                    messages.warning(request, 'Please change your temporary password before continuing.')
                    return redirect('accounts:force_password_change')

        response = self.get_response(request)
        return response 