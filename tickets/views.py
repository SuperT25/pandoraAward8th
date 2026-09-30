"""
Pandora E-Ticket System — Views (all phases)
"""

import csv
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .decorators import (
    super_admin_required, ticket_admin_required,
    walkin_staff_required, verify_staff_required,
)
from .forms import (
    GuestRegistrationForm, TicketCreateForm, WalkInRegistrationForm,
    EventForm, TicketTypeForm, StaffCreateForm, StaffEditForm,
    VerifyTicketForm, GuestPhotoForm,
)
from .models import Event, Guest, Ticket, TicketType, UserProfile, VerificationLog
from .utils import get_client_ip, generate_ticket_pdf, save_qr_to_file


# ===========================================================================
# AUTH
# ===========================================================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'dashboard'))
        messages.error(request, 'Invalid username or password.')
    return render(request, 'tickets/login.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


# ===========================================================================
# DASHBOARD
# ===========================================================================

@login_required
def dashboard(request):
    active_event = Event.objects.filter(active=True).first()

    total = Ticket.objects.count()
    pre_reg = Ticket.objects.filter(guest__registration_source='PRE_REGISTERED').count()
    walk_in = Ticket.objects.filter(guest__registration_source='WALK_IN').count()
    checked_in = Ticket.objects.filter(status='USED').count()
    not_checked_in = Ticket.objects.filter(status='ACTIVE').count()
    cancelled = Ticket.objects.filter(status='CANCELLED').count()

    # Breakdown by ticket type
    breakdown = (
        TicketType.objects.filter(active=True)
        .annotate(total=Count('tickets'), used=Count('tickets', filter=Q(tickets__status='USED')))
        .values('name', 'total', 'used')
    )

    # Recent check-ins
    recent_checkins = (
        Ticket.objects.filter(status='USED')
        .select_related('guest', 'ticket_type', 'checked_in_by')
        .order_by('-checked_in_at')[:10]
    )

    ctx = {
        'active_event': active_event,
        'total': total,
        'pre_reg': pre_reg,
        'walk_in': walk_in,
        'checked_in': checked_in,
        'not_checked_in': not_checked_in,
        'cancelled': cancelled,
        'breakdown': breakdown,
        'recent_checkins': recent_checkins,
    }
    return render(request, 'tickets/dashboard.html', ctx)


# ===========================================================================
# GUEST MANAGEMENT
# ===========================================================================

@login_required
@ticket_admin_required
def guest_list(request):
    q = request.GET.get('q', '').strip()
    guests = Guest.objects.prefetch_related('tickets').order_by('-created_at')
    if q:
        guests = guests.filter(
            Q(full_name__icontains=q) | Q(phone_number__icontains=q) | Q(email__icontains=q)
        )
    return render(request, 'tickets/guest_list.html', {'guests': guests, 'q': q})


@login_required
@ticket_admin_required
def guest_create(request):
    if request.method == 'POST':
        guest_form = GuestRegistrationForm(request.POST, request.FILES)
        ticket_form = TicketCreateForm(request.POST)
        if guest_form.is_valid() and ticket_form.is_valid():
            guest = guest_form.save(commit=False)
            guest.registration_source = Guest.RegistrationSource.PRE_REGISTERED
            guest.save()

            ticket = ticket_form.save(commit=False)
            ticket.guest = guest
            ticket.save()
            save_qr_to_file(ticket)

            messages.success(request, f"Ticket {ticket.ticket_number} created for {guest.full_name}.")
            return redirect('ticket_detail', pk=ticket.pk)
    else:
        guest_form = GuestRegistrationForm()
        ticket_form = TicketCreateForm()
    return render(request, 'tickets/guest_create.html', {
        'guest_form': guest_form, 'ticket_form': ticket_form,
    })


@login_required
@ticket_admin_required
def guest_detail(request, pk):
    guest = get_object_or_404(Guest, pk=pk)
    tickets = guest.tickets.select_related('event', 'ticket_type', 'checked_in_by').all()
    photo_form = GuestPhotoForm(instance=guest)
    if request.method == 'POST':
        photo_form = GuestPhotoForm(request.POST, request.FILES, instance=guest)
        if photo_form.is_valid():
            photo_form.save()
            messages.success(request, "Photo updated.")
            return redirect('guest_detail', pk=pk)
    return render(request, 'tickets/guest_detail.html', {
        'guest': guest, 'tickets': tickets, 'photo_form': photo_form,
    })


# ===========================================================================
# TICKET MANAGEMENT
# ===========================================================================

@login_required
@ticket_admin_required
def ticket_list(request):
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    tickets = Ticket.objects.select_related('guest', 'event', 'ticket_type', 'checked_in_by').order_by('-created_at')
    if q:
        tickets = tickets.filter(
            Q(ticket_number__icontains=q)
            | Q(guest__full_name__icontains=q)
            | Q(guest__phone_number__icontains=q)
        )
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    return render(request, 'tickets/ticket_list.html', {
        'tickets': tickets, 'q': q, 'status_filter': status_filter,
    })


@login_required
@ticket_admin_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(
        Ticket.objects.select_related('guest', 'event', 'ticket_type', 'checked_in_by'), pk=pk
    )
    logs = ticket.verification_logs.select_related('staff_user').order_by('-timestamp')[:20]
    return render(request, 'tickets/ticket_detail.html', {'ticket': ticket, 'logs': logs})


@login_required
def ticket_download(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    # All logged-in roles may download
    pdf_bytes = generate_ticket_pdf(ticket)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    fname = f"Pandora_Ticket_{ticket.ticket_number}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{fname}"'
    return response


@login_required
def ticket_view_pdf(request, pk):
    """Inline PDF view (for preview in browser)."""
    ticket = get_object_or_404(Ticket, pk=pk)
    pdf_bytes = generate_ticket_pdf(ticket)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    fname = f"Pandora_Ticket_{ticket.ticket_number}.pdf"
    response['Content-Disposition'] = f'inline; filename="{fname}"'
    return response


@login_required
@ticket_admin_required
def ticket_cancel(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not request.user.profile.can_cancel_ticket:
        messages.error(request, "You do not have permission to cancel tickets.")
        return redirect('ticket_detail', pk=pk)
    if request.method == 'POST':
        if ticket.status == Ticket.Status.CANCELLED:
            messages.warning(request, "Ticket is already cancelled.")
        else:
            ticket.status = Ticket.Status.CANCELLED
            ticket.cancelled_at = timezone.now()
            ticket.save()
            VerificationLog.objects.create(
                ticket=ticket,
                staff_user=request.user,
                action=VerificationLog.Action.REJECT,
                result=VerificationLog.Result.CANCELLED,
                ip_address=get_client_ip(request),
                notes="Cancelled via admin portal.",
            )
            messages.success(request, f"Ticket {ticket.ticket_number} has been cancelled.")
        return redirect('ticket_detail', pk=pk)
    return render(request, 'tickets/ticket_cancel_confirm.html', {'ticket': ticket})


# ===========================================================================
# VERIFICATION PORTAL
# ===========================================================================

@login_required
@verify_staff_required
def verify_portal(request):
    form = VerifyTicketForm()
    return render(request, 'tickets/verify_portal.html', {'form': form})


@login_required
@verify_staff_required
@require_POST
def verify_search(request):
    """POST — search by ticket number or phone number."""
    query = request.POST.get('query', '').strip()
    if not query:
        messages.warning(request, "Please enter a ticket number or phone number.")
        return redirect('verify_portal')

    ip = get_client_ip(request)

    # Try ticket number first
    ticket = Ticket.objects.filter(ticket_number__iexact=query).select_related(
        'guest', 'event', 'ticket_type', 'checked_in_by'
    ).first()

    if ticket:
        _log_verify(ticket, request.user, ip, query)
        return _render_ticket_result(request, ticket)

    # Try phone number
    guests = Guest.objects.filter(phone_number__icontains=query).prefetch_related('tickets')
    if guests.exists():
        all_tickets = Ticket.objects.filter(guest__in=guests).select_related(
            'guest', 'event', 'ticket_type', 'checked_in_by'
        ).order_by('-created_at')
        if all_tickets.count() == 1:
            ticket = all_tickets.first()
            _log_verify(ticket, request.user, ip, query)
            return _render_ticket_result(request, ticket)
        # Multiple tickets — show selection
        for t in all_tickets:
            VerificationLog.objects.create(
                ticket=t, staff_user=request.user,
                action=VerificationLog.Action.SEARCH,
                result=VerificationLog.Result.VALID if t.is_active else VerificationLog.Result.ALREADY_USED,
                ip_address=ip, notes=f"Phone search: {query}",
            )
        return render(request, 'tickets/verify_multiple.html', {'tickets': all_tickets, 'query': query})

    # Not found
    VerificationLog.objects.create(
        ticket=None, staff_user=request.user,
        action=VerificationLog.Action.SEARCH,
        result=VerificationLog.Result.INVALID,
        ip_address=ip,
        notes=f"Not found: {query}",
    )
    return render(request, 'tickets/verify_result.html', {
        'result': 'INVALID', 'query': query,
    })


@login_required
@verify_staff_required
def verify_by_qr(request, qr_token):
    """Called by QR scanner redirect: /verify/qr/<token>/"""
    ip = get_client_ip(request)
    ticket = Ticket.objects.filter(qr_token=qr_token).select_related(
        'guest', 'event', 'ticket_type', 'checked_in_by'
    ).first()

    if not ticket:
        VerificationLog.objects.create(
            ticket=None, staff_user=request.user,
            action=VerificationLog.Action.VERIFY,
            result=VerificationLog.Result.INVALID,
            ip_address=ip,
            notes=f"QR token not found: {qr_token[:16]}...",
        )
        return render(request, 'tickets/verify_result.html', {'result': 'INVALID', 'query': qr_token})

    _log_verify(ticket, request.user, ip, f"QR: {qr_token[:8]}...")
    return _render_ticket_result(request, ticket)


def _log_verify(ticket, user, ip, notes=''):
    if ticket.is_active:
        result = VerificationLog.Result.VALID
    elif ticket.is_used:
        result = VerificationLog.Result.ALREADY_USED
    else:
        result = VerificationLog.Result.CANCELLED
    VerificationLog.objects.create(
        ticket=ticket, staff_user=user,
        action=VerificationLog.Action.VERIFY,
        result=result, ip_address=ip, notes=notes,
    )


def _render_ticket_result(request, ticket):
    if ticket.is_active:
        result = 'VALID'
    elif ticket.is_used:
        result = 'ALREADY_USED'
    else:
        result = 'CANCELLED'
    return render(request, 'tickets/verify_result.html', {
        'result': result, 'ticket': ticket,
    })


# ===========================================================================
# CHECK-IN  (atomic — prevents double check-in)
# ===========================================================================

@login_required
@verify_staff_required
@require_POST
def checkin(request, pk):
    ip = get_client_ip(request)
    with transaction.atomic():
        # select_for_update locks the row until commit
        ticket = get_object_or_404(
            Ticket.objects.select_for_update().select_related('guest', 'event', 'ticket_type'),
            pk=pk
        )
        if ticket.status != Ticket.Status.ACTIVE:
            # Already used or cancelled — reject
            VerificationLog.objects.create(
                ticket=ticket, staff_user=request.user,
                action=VerificationLog.Action.CHECK_IN,
                result=VerificationLog.Result.ALREADY_USED if ticket.is_used else VerificationLog.Result.CANCELLED,
                ip_address=ip, notes="Duplicate check-in attempt blocked.",
            )
            return render(request, 'tickets/verify_result.html', {
                'result': 'ALREADY_USED' if ticket.is_used else 'CANCELLED',
                'ticket': ticket,
            })

        ticket.status = Ticket.Status.USED
        ticket.checked_in_at = timezone.now()
        ticket.checked_in_by = request.user
        ticket.save()

        VerificationLog.objects.create(
            ticket=ticket, staff_user=request.user,
            action=VerificationLog.Action.CHECK_IN,
            result=VerificationLog.Result.VALID,
            ip_address=ip, notes="Guest checked in successfully.",
        )

    return render(request, 'tickets/checkin_success.html', {'ticket': ticket})


# ===========================================================================
# WALK-IN REGISTRATION
# ===========================================================================

@login_required
@walkin_staff_required
def walkin_register(request):
    if request.method == 'POST':
        form = WalkInRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            guest = Guest.objects.create(
                full_name=form.cleaned_data['full_name'],
                phone_number=form.cleaned_data['phone_number'],
                email=form.cleaned_data.get('email', ''),
                photo=form.cleaned_data.get('photo'),
                registration_source=Guest.RegistrationSource.WALK_IN,
            )
            ticket = Ticket.objects.create(
                guest=guest,
                event=form.cleaned_data['event'],
                ticket_type=form.cleaned_data['ticket_type'],
            )
            save_qr_to_file(ticket)
            messages.success(request, f"Walk-in ticket {ticket.ticket_number} generated for {guest.full_name}.")
            return redirect('verify_result_direct', pk=ticket.pk)
    else:
        form = WalkInRegistrationForm()
    return render(request, 'tickets/walkin_register.html', {'form': form})


@login_required
@login_required
@verify_staff_required
def verify_result_direct(request, pk):
    """Show verify result for a freshly generated walk-in ticket.
    Result is derived from actual ticket status — never hardcoded."""
    ticket = get_object_or_404(
        Ticket.objects.select_related('guest', 'event', 'ticket_type', 'checked_in_by'), pk=pk
    )
    # Derive result from real ticket status — fixes hardcoded VALID bypass
    if ticket.is_active:
        result = 'VALID'
    elif ticket.is_used:
        result = 'ALREADY_USED'
    else:
        result = 'CANCELLED'
    return render(request, 'tickets/verify_result.html', {
        'result': result, 'ticket': ticket,
    })


# ===========================================================================
# EVENTS
# ===========================================================================

@login_required
@super_admin_required
def event_list(request):
    events = Event.objects.all()
    return render(request, 'tickets/event_list.html', {'events': events})


@login_required
@super_admin_required
def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Event created.")
            return redirect('event_list')
    else:
        form = EventForm()
    return render(request, 'tickets/event_form.html', {'form': form, 'title': 'New Event'})


@login_required
@super_admin_required
def event_edit(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, "Event updated.")
            return redirect('event_list')
    else:
        form = EventForm(instance=event)
    return render(request, 'tickets/event_form.html', {'form': form, 'title': 'Edit Event'})


# ===========================================================================
# TICKET TYPES
# ===========================================================================

@login_required
@super_admin_required
def tickettype_list(request):
    types = TicketType.objects.all()
    return render(request, 'tickets/tickettype_list.html', {'types': types})


@login_required
@super_admin_required
def tickettype_create(request):
    if request.method == 'POST':
        form = TicketTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Ticket type created.")
            return redirect('tickettype_list')
    else:
        form = TicketTypeForm()
    return render(request, 'tickets/tickettype_form.html', {'form': form, 'title': 'New Ticket Type'})


@login_required
@super_admin_required
def tickettype_edit(request, pk):
    tt = get_object_or_404(TicketType, pk=pk)
    if request.method == 'POST':
        form = TicketTypeForm(request.POST, instance=tt)
        if form.is_valid():
            form.save()
            messages.success(request, "Ticket type updated.")
            return redirect('tickettype_list')
    else:
        form = TicketTypeForm(instance=tt)
    return render(request, 'tickets/tickettype_form.html', {'form': form, 'title': 'Edit Ticket Type'})


# ===========================================================================
# STAFF / USER MANAGEMENT
# ===========================================================================

@login_required
@super_admin_required
def staff_list(request):
    profiles = UserProfile.objects.select_related('user').order_by('user__username')
    return render(request, 'tickets/staff_list.html', {'profiles': profiles})


@login_required
@super_admin_required
def staff_create(request):
    if request.method == 'POST':
        form = StaffCreateForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data.get('email', ''),
            )
            UserProfile.objects.create(user=user, role=form.cleaned_data['role'])
            messages.success(request, f"Staff account '{user.username}' created.")
            return redirect('staff_list')
    else:
        form = StaffCreateForm()
    return render(request, 'tickets/staff_form.html', {'form': form, 'title': 'Create Staff Account'})


@login_required
@super_admin_required
def staff_edit(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    user = profile.user
    if request.method == 'POST':
        form = StaffEditForm(request.POST)
        if form.is_valid():
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data.get('email', '')
            user.is_active = form.cleaned_data.get('is_active', True)
            user.save()
            profile.role = form.cleaned_data['role']
            profile.save()
            messages.success(request, "Staff account updated.")
            return redirect('staff_list')
    else:
        form = StaffEditForm(initial={
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'role': profile.role,
            'is_active': user.is_active,
        })
    return render(request, 'tickets/staff_form.html', {'form': form, 'title': 'Edit Staff Account', 'profile': profile})


# ===========================================================================
# REPORTS
# ===========================================================================

@login_required
@ticket_admin_required
def reports(request):
    tickets = Ticket.objects.select_related(
        'guest', 'event', 'ticket_type', 'checked_in_by'
    ).order_by('-created_at')

    # Filters
    source_filter = request.GET.get('source', '')
    status_filter = request.GET.get('status', '')
    ttype_filter = request.GET.get('ticket_type', '')

    if source_filter:
        tickets = tickets.filter(guest__registration_source=source_filter)
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if ttype_filter:
        tickets = tickets.filter(ticket_type__name__iexact=ttype_filter)

    ticket_types = TicketType.objects.filter(active=True)
    return render(request, 'tickets/reports.html', {
        'tickets': tickets,
        'source_filter': source_filter,
        'status_filter': status_filter,
        'ttype_filter': ttype_filter,
        'ticket_types': ticket_types,
    })


@login_required
@ticket_admin_required
def reports_export_csv(request):
    tickets = Ticket.objects.select_related(
        'guest', 'event', 'ticket_type', 'checked_in_by'
    ).order_by('-created_at')

    source_filter = request.GET.get('source', '')
    status_filter = request.GET.get('status', '')
    ttype_filter = request.GET.get('ticket_type', '')

    if source_filter:
        tickets = tickets.filter(guest__registration_source=source_filter)
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if ttype_filter:
        tickets = tickets.filter(ticket_type__name__iexact=ttype_filter)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="pandora_tickets_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Guest Name', 'Phone Number', 'Email',
        'Ticket Number', 'Ticket Type', 'Registration Source',
        'Event', 'Status', 'Issued At', 'Check-In Time', 'Checked In By',
    ])

    for t in tickets:
        writer.writerow([
            t.guest.full_name,
            t.guest.phone_number,
            t.guest.email,
            t.ticket_number,
            t.ticket_type.name,
            t.guest.get_registration_source_display(),
            t.event.event_name,
            t.status,
            t.issued_at.strftime('%Y-%m-%d %H:%M') if t.issued_at else '',
            t.checked_in_at.strftime('%Y-%m-%d %H:%M') if t.checked_in_at else '',
            t.checked_in_by.get_full_name() if t.checked_in_by else '',
        ])

    return response


# ===========================================================================
# VERIFICATION LOG
# ===========================================================================

@login_required
@ticket_admin_required
def verification_log(request):
    logs = VerificationLog.objects.select_related('ticket', 'staff_user').order_by('-timestamp')[:200]
    return render(request, 'tickets/verification_log.html', {'logs': logs})
