"""
Management command: python manage.py regenerate_qr
Regenerates all QR code files with the full live verify URL.
Run this once after deploying the QR URL fix.
"""

from django.core.management.base import BaseCommand
from tickets.models import Ticket
from tickets.utils import save_qr_to_file


class Command(BaseCommand):
    help = 'Regenerate all QR codes with full live verify URL.'

    def handle(self, *args, **options):
        tickets = Ticket.objects.all()
        total = tickets.count()
        self.stdout.write(f'Regenerating QR codes for {total} tickets...')
        ok = 0
        for ticket in tickets:
            try:
                save_qr_to_file(ticket)
                ok += 1
                self.stdout.write(f'  ✔ {ticket.ticket_number}')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✘ {ticket.ticket_number}: {e}'))
        self.stdout.write(self.style.SUCCESS(f'\nDone. {ok}/{total} QR codes regenerated.'))
