from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        import core.signals

 # Signal receiver to create auth tokens when a new user is created.
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """
    This signal receiver is triggered after a new user is created.
    It checks if the user is new (`created=True`) and if so,
    it creates a new `Token` for that user.
    """
    from rest_framework.authtoken.models import Token
    if created:
        Token.objects.create(user=instance)
