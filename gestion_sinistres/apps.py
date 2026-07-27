from django.apps import AppConfig


class GestionSinistresConfig(AppConfig):
    name = 'gestion_sinistres'

    def ready(self):
        from . import signals
