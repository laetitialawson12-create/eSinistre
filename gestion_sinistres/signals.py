from django.contrib.auth.signals import user_login_failed, user_logged_in
from django.dispatch import receiver
from .auth_utils import enregistrer_echec, reinitialiser_tentatives

@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    identifiant = credentials.get('username')
    enregistrer_echec(identifiant)


@receiver(user_logged_in)
def on_login_success(sender, user, request=None, **kwargs):
    profil = (
        getattr(user, 'assure', None)
        or getattr(user, 'agent', None)
        or getattr(user, 'chef', None)
    )
    reinitialiser_tentatives(profil)