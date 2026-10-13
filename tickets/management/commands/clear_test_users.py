"""
Management command: python manage.py clear_test_users
Deletes all staff/user accounts except pandoraadmin.
Run this once on Render after deploying.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Delete all staff accounts except pandoraadmin.'

    def handle(self, *args, **options):
        deleted = User.objects.exclude(username='pandoraadmin').delete()
        self.stdout.write(self.style.SUCCESS(
            f'Deleted {deleted[0]} accounts. Only pandoraadmin remains.'
        ))
