"""
Pandora E-Ticket System — Role-based access decorators
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def role_required(*roles):
    """Restrict a view to users whose profile.role is in the given list."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            try:
                user_role = request.user.profile.role
            except Exception:
                messages.error(request, "Your account has no role assigned. Contact the administrator.")
                return redirect('login')
            if user_role not in roles:
                messages.error(request, "You do not have permission to access that page.")
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def super_admin_required(view_func):
    return role_required('SUPER_ADMIN')(view_func)


def ticket_admin_required(view_func):
    return role_required('SUPER_ADMIN', 'TICKET_ADMIN')(view_func)


def walkin_staff_required(view_func):
    return role_required('SUPER_ADMIN', 'TICKET_ADMIN', 'WALKIN_STAFF')(view_func)


def verify_staff_required(view_func):
    return role_required('SUPER_ADMIN', 'TICKET_ADMIN', 'VERIFICATION_STAFF', 'WALKIN_STAFF')(view_func)
