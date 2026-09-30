"""
Auto-create UserProfile when a new User is created (e.g. via createsuperuser).
"""

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if not hasattr(instance, 'profile'):
            role = UserProfile.Role.SUPER_ADMIN if instance.is_superuser else UserProfile.Role.VERIFICATION_STAFF
            UserProfile.objects.create(user=instance, role=role)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
