"""
Pandora E-Ticket System — Role-based access decorators

Two roles:
  ADMIN  — full access (register guests, manage tickets, reports, events, staff)
  STAFF  — verification only (search, verify, check-in)
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*roles):
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
                return redirect('verify_portal')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def admin_required(view_func):
    """Admin only — full access."""
    return role_required('ADMIN')(view_func)


def any_staff_required(view_func):
    """Both ADMIN and STAFF can access — used for verify/check-in views."""
    return role_required('ADMIN', 'STAFF')(view_func)


# Aliases for backward compatibility with existing view decorators
super_admin_required  = admin_required
ticket_admin_required = admin_required
walkin_staff_required = any_staff_required
verify_staff_required = any_staff_required
