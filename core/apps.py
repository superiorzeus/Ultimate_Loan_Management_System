# core/apps.py:

from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # We need to import the signals file to ensure that the loan-related signals are registered.
        import core.signals


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """
    This signal receiver is triggered after a new user is created.
    It checks if the user is new (`created=True`) and if so,
    it creates a new `Token` for that user.
    """
    # The import for the Token model is placed here to avoid
    # the AppRegistryNotReady error, as it's only called after
    # the app registry is fully initialized.
    from rest_framework.authtoken.models import Token
    
    # Only create a token if a new user instance has been created.
    if created:
        Token.objects.create(user=instance)

