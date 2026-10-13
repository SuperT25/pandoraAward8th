"""
Management command: python manage.py clear_all_data
Clears ALL guests, tickets, logs and staff accounts.
Keeps only the pandoraadmin account.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from tickets.models import Guest, Ticket, VerificationLog, ReEntryLog


class Command(BaseCommand):
    help = 'Clear all guests, tickets, logs and staff. Keep pandoraadmin only.'

    def handle(self, *args, **options):
        # Clear logs first (FK dependencies)
        rl = ReEntryLog.objects.all().delete()
        vl = VerificationLog.objects.all().delete()
        t  = Ticket.objects.all().delete()
        g  = Guest.objects.all().delete()
        u  = User.objects.exclude(username='pandoraadmin').delete()

        self.stdout.write(self.style.SUCCESS('✔ Re-entry logs deleted'))
        self.stdout.write(self.style.SUCCESS('✔ Verification logs deleted'))
        self.stdout.write(self.style.SUCCESS(f'✔ Tickets deleted: {t[0]}'))
        self.stdout.write(self.style.SUCCESS(f'✔ Guests deleted: {g[0]}'))
        self.stdout.write(self.style.SUCCESS(f'✔ Staff accounts deleted: {u[0]}'))
        self.stdout.write(self.style.SUCCESS('\nAll clear. Only pandoraadmin remains. 🏆'))
