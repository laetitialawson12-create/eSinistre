from django.contrib.auth.backends import ModelBackend
from .models import Assure


class NumeroPoliceBackend(ModelBackend):
    """
    Authentifie un assuré à partir de son numéro de police
    (saisi dans le champ 'username' du formulaire de connexion),
    plutôt qu'à partir d'un nom d'utilisateur technique.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        assure = Assure.objects.filter(numero_police=username).select_related('user').first()
        if not assure:
            return None

        user = assure.user
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None