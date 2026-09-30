"""
Pandora E-Ticket System — URL Configuration
"""

from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Guests
    path('guests/', views.guest_list, name='guest_list'),
    path('guests/create/', views.guest_create, name='guest_create'),
    path('guests/<int:pk>/', views.guest_detail, name='guest_detail'),

    # Tickets
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<int:pk>/download/', views.ticket_download, name='ticket_download'),
    path('tickets/<int:pk>/view/', views.ticket_view_pdf, name='ticket_view_pdf'),
    path('tickets/<int:pk>/cancel/', views.ticket_cancel, name='ticket_cancel'),

    # Verification portal
    path('verify/', views.verify_portal, name='verify_portal'),
    path('verify/search/', views.verify_search, name='verify_search'),
    path('verify/qr/<slug:qr_token>/', views.verify_by_qr, name='verify_by_qr'),
    path('verify/direct/<int:pk>/', views.verify_result_direct, name='verify_result_direct'),

    # Check-in
    path('checkin/<int:pk>/', views.checkin, name='checkin'),

    # Walk-in
    path('walk-in/', views.walkin_register, name='walkin_register'),

    # Events
    path('events/', views.event_list, name='event_list'),
    path('events/create/', views.event_create, name='event_create'),
    path('events/<int:pk>/edit/', views.event_edit, name='event_edit'),

    # Ticket types
    path('ticket-types/', views.tickettype_list, name='tickettype_list'),
    path('ticket-types/create/', views.tickettype_create, name='tickettype_create'),
    path('ticket-types/<int:pk>/edit/', views.tickettype_edit, name='tickettype_edit'),

    # Staff management
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/create/', views.staff_create, name='staff_create'),
    path('staff/<int:pk>/edit/', views.staff_edit, name='staff_edit'),

    # Reports
    path('reports/', views.reports, name='reports'),
    path('reports/export/', views.reports_export_csv, name='reports_export_csv'),

    # Verification log
    path('logs/', views.verification_log, name='verification_log'),
]
