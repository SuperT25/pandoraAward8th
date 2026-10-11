"""
Pandora E-Ticket System — Role-based access decorators

Three roles:
  ADMIN      — full access
  GATE_STAFF — Gate 1 (venue entrance): verify/search only, no check-in
  HALL_STAFF — Gate 2 (event hall): verify + check-in
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
    """Admin only."""
    return role_required('ADMIN')(view_func)


def verify_staff_required(view_func):
    """All roles can access verify pages."""
    return role_required('ADMIN', 'GATE_STAFF', 'HALL_STAFF')(view_func)


def checkin_required(view_func):
    """Only ADMIN and HALL_STAFF can check in guests."""
    return role_required('ADMIN', 'HALL_STAFF')(view_func)


# Aliases for backward compatibility
super_admin_required  = admin_required
ticket_admin_required = admin_required
walkin_staff_required = admin_required
any_staff_required    = verify_staff_required
