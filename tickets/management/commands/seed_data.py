"""
Management command: python manage.py seed_data
Seeds the Pandora Awards 8th Edition event, ticket types,
and creates a default superadmin account.
"""

import datetime
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from tickets.models import Event, TicketType, UserProfile


class Command(BaseCommand):
    help = 'Seed Pandora Awards 8th Edition event data and default admin account.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding Pandora Awards 8th Edition data...'))

        # ── Event ──────────────────────────────────────────────────────────
        event, created = Event.objects.get_or_create(
            event_name='Pandora Awards 8th Edition',
            defaults={
                'description': (
                    'An unforgettable evening of celebration, recognition, glamour and excellence. '
                    'Pandora Awards 2026 — Live in Abuja. 🏆✨'
                ),
                'venue': 'A Class Event Center, Sapphire Hall, Along Kashmiri Ibrahim Way, Maitama, Abuja',
                'event_date': datetime.date(2026, 11, 29),
                'event_time': datetime.time(16, 0),   # Red carpet 4 PM
                'active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  ✔ Event created: Pandora Awards 8th Edition'))
        else:
            self.stdout.write('  — Event already exists.')

        # ── Ticket types ───────────────────────────────────────────────────
        types = [
            ('Regular',             'Standard event admission — Red Carpet from 4 PM'),
            ('VIP',                 'VIP admission with premium seating'),
            ('Special Guest Seat',  'Exclusive Special Guest Seat with premium privileges'),
            ('Gold Table',          'Exclusive Gold Table reservation for groups'),
            ('Media',               'Media & Press accreditation'),
            ('Staff',               'Event staff and crew access'),
        ]
        for name, desc in types:
            tt, created = TicketType.objects.get_or_create(name=name, defaults={'description': desc, 'active': True})
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✔ Ticket type: {name}'))
            else:
                self.stdout.write(f'  — Ticket type already exists: {name}')

        # ── Super admin account ────────────────────────────────────────────
        if not User.objects.filter(username='pandoraadmin').exists():
            user = User.objects.create_superuser(
                username='pandoraadmin',
                password='Pandora@2026!',
                first_name='Pandora',
                last_name='Administrator',
                email='info.pandoraawards@gmail.com',
            )
            # Signal will create profile, update role to SUPER_ADMIN
            try:
                user.profile.role = UserProfile.Role.SUPER_ADMIN
                user.profile.save()
            except Exception:
                UserProfile.objects.create(user=user, role=UserProfile.Role.SUPER_ADMIN)
            self.stdout.write(self.style.SUCCESS(
                '  ✔ Super admin created — username: pandoraadmin  password: Pandora@2026!'
            ))
            self.stdout.write(self.style.WARNING(
                '  ⚠  CHANGE THIS PASSWORD immediately after first login!'
            ))
        else:
            self.stdout.write('  — Admin account already exists.')

        self.stdout.write(self.style.SUCCESS('\nSeed complete. 🏆'))
