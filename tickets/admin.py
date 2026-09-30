"""
Pandora E-Ticket System — Django Admin
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Event, TicketType, Guest, Ticket, VerificationLog, UserProfile


# ---------------------------------------------------------------------------
# Inline UserProfile in User admin
# ---------------------------------------------------------------------------

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile & Role'
    fk_name = 'user'


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('event_name', 'venue', 'event_date', 'event_time', 'active')
    list_filter = ('active', 'event_date')
    search_fields = ('event_name', 'venue')


# ---------------------------------------------------------------------------
# TicketType
# ---------------------------------------------------------------------------

@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'created_at')
    list_filter = ('active',)


# ---------------------------------------------------------------------------
# Guest
# ---------------------------------------------------------------------------

@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone_number', 'email', 'registration_source', 'created_at')
    list_filter = ('registration_source',)
    search_fields = ('full_name', 'phone_number', 'email')


# ---------------------------------------------------------------------------
# Ticket
# ---------------------------------------------------------------------------

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'guest', 'event', 'ticket_type', 'status', 'issued_at', 'checked_in_at')
    list_filter = ('status', 'ticket_type', 'event')
    search_fields = ('ticket_number', 'guest__full_name', 'guest__phone_number')
    readonly_fields = ('ticket_number', 'qr_token', 'issued_at', 'checked_in_at', 'created_at', 'updated_at')


# ---------------------------------------------------------------------------
# VerificationLog
# ---------------------------------------------------------------------------

@admin.register(VerificationLog)
class VerificationLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action', 'result', 'ticket', 'staff_user', 'ip_address')
    list_filter = ('action', 'result')
    search_fields = ('ticket__ticket_number',)
    readonly_fields = ('timestamp',)
