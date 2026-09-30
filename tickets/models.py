"""
Pandora E-Ticket System — Core Models
"""

import secrets
import string
import uuid
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate_ticket_number():
    """Generate a unique ticket number like PDR26-X7K92M."""
    chars = string.ascii_uppercase + string.digits
    year = timezone.now().year % 100  # e.g. 26
    suffix = ''.join(secrets.choice(chars) for _ in range(6))
    return f"PDR{year:02d}-{suffix}"


def generate_qr_token():
    """Cryptographically secure QR token — UUID4 hex, 32 chars."""
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------

class Event(models.Model):
    event_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    venue = models.CharField(max_length=300)
    event_date = models.DateField()
    event_time = models.TimeField()
    logo = models.ImageField(upload_to='events/logos/', blank=True, null=True)
    background = models.ImageField(upload_to='events/backgrounds/', blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-event_date']

    def __str__(self):
        return self.event_name


# ---------------------------------------------------------------------------
# TicketType
# ---------------------------------------------------------------------------

class TicketType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Guest
# ---------------------------------------------------------------------------

class Guest(models.Model):
    class RegistrationSource(models.TextChoices):
        PRE_REGISTERED = 'PRE_REGISTERED', 'Pre-Registered'
        WALK_IN = 'WALK_IN', 'Walk-In'

    full_name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    photo = models.ImageField(upload_to='photos/', blank=True, null=True)
    registration_source = models.CharField(
        max_length=20,
        choices=RegistrationSource.choices,
        default=RegistrationSource.PRE_REGISTERED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"


# ---------------------------------------------------------------------------
# Ticket
# ---------------------------------------------------------------------------

class Ticket(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        USED = 'USED', 'Used'
        CANCELLED = 'CANCELLED', 'Cancelled'

    guest = models.ForeignKey(Guest, on_delete=models.PROTECT, related_name='tickets')
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name='tickets')
    ticket_type = models.ForeignKey(TicketType, on_delete=models.PROTECT, related_name='tickets')
    ticket_number = models.CharField(max_length=20, unique=True, editable=False)
    qr_token = models.CharField(max_length=64, unique=True, editable=False)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='checked_in_tickets',
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            candidate = generate_ticket_number()
            while Ticket.objects.filter(ticket_number=candidate).exists():
                candidate = generate_ticket_number()
            self.ticket_number = candidate
        if not self.qr_token:
            candidate = generate_qr_token()
            while Ticket.objects.filter(qr_token=candidate).exists():
                candidate = generate_qr_token()
            self.qr_token = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_number} — {self.guest.full_name}"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def is_used(self):
        return self.status == self.Status.USED

    @property
    def is_cancelled(self):
        return self.status == self.Status.CANCELLED


# ---------------------------------------------------------------------------
# VerificationLog
# ---------------------------------------------------------------------------

class VerificationLog(models.Model):
    class Action(models.TextChoices):
        SEARCH = 'SEARCH', 'Search'
        VERIFY = 'VERIFY', 'Verify'
        CHECK_IN = 'CHECK_IN', 'Check-In'
        REJECT = 'REJECT', 'Reject'

    class Result(models.TextChoices):
        VALID = 'VALID', 'Valid'
        INVALID = 'INVALID', 'Invalid'
        ALREADY_USED = 'ALREADY_USED', 'Already Used'
        CANCELLED = 'CANCELLED', 'Cancelled'

    ticket = models.ForeignKey(
        Ticket, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='verification_logs',
    )
    staff_user = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='verification_logs',
    )
    action = models.CharField(max_length=10, choices=Action.choices)
    result = models.CharField(max_length=14, choices=Result.choices)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} / {self.result} @ {self.timestamp:%Y-%m-%d %H:%M}"


# ---------------------------------------------------------------------------
# UserProfile — role management
# ---------------------------------------------------------------------------

class UserProfile(models.Model):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
        TICKET_ADMIN = 'TICKET_ADMIN', 'Ticket Admin'
        VERIFICATION_STAFF = 'VERIFICATION_STAFF', 'Verification Staff'
        WALKIN_STAFF = 'WALKIN_STAFF', 'Walk-In Registration Staff'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=25, choices=Role.choices, default=Role.VERIFICATION_STAFF)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

    @property
    def is_ticket_admin(self):
        return self.role in (self.Role.SUPER_ADMIN, self.Role.TICKET_ADMIN)

    @property
    def can_register_walkin(self):
        return self.role in (
            self.Role.SUPER_ADMIN,
            self.Role.TICKET_ADMIN,
            self.Role.WALKIN_STAFF,
        )

    @property
    def can_cancel_ticket(self):
        return self.role in (self.Role.SUPER_ADMIN, self.Role.TICKET_ADMIN)

    @property
    def can_manage_events(self):
        return self.role == self.Role.SUPER_ADMIN

    @property
    def can_manage_users(self):
        return self.role == self.Role.SUPER_ADMIN
