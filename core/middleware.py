import time
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages

class AutoLogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # We only care about users who are currently logged in
        if request.user.is_authenticated:
            current_time = time.time()
            
            # Get the last activity time from the session (default to now if it doesn't exist)
            last_activity = request.session.get('last_activity', current_time)
            
            idle_duration = current_time - last_activity
            
            # Get timeout duration from settings (default to 15 mins), convert to seconds
            timeout = getattr(settings, 'AUTO_LOGOUT_DELAY', 15) * 60 
            
            if idle_duration > timeout:
                # The user has been idle too long. Destroy the session.
                logout(request)
                messages.error(request, 'Your session has expired due to inactivity. Please log in again securely.')
                return redirect('login') 
            
            # The user is active. Update the timestamp for their next click.
            request.session['last_activity'] = current_time

        response = self.get_response(request)
        return response