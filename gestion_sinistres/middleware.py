from datetime import timedelta
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import logout
from django.utils import timezone


class InactiviteMiddleware:
    DELAI_INACTIVITE = timedelta(minutes=5)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            derniere_activite = request.session.get('derniere_activite')
            maintenant = timezone.now().timestamp()

            if derniere_activite and (maintenant - derniere_activite) > self.DELAI_INACTIVITE.total_seconds():
                logout(request)
                return redirect('login')

            request.session['derniere_activite'] = maintenant

        return self.get_response(request)


class PolitiqueConfidentialiteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            assure = getattr(request.user, 'assure', None)
            if assure and not assure.politique_confidentialite_acceptee:
                urls_autorisees = [
                    reverse('politique_confidentialite'),
                    reverse('logout'),
                ]
                chemins_exclus = ('/static/', '/media/')
                if request.path not in urls_autorisees and not request.path.startswith(chemins_exclus):
                    return redirect('politique_confidentialite')

        return self.get_response(request)
    

class MotDePasseTemporaireMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            agent = getattr(request.user, 'agent', None)
            if agent and agent.doit_changer_mot_de_passe:
                urls_autorisees = [reverse('changer_mot_de_passe_agent'), reverse('logout')]
                chemins_exclus = ('/static/', '/media/')
                if request.path not in urls_autorisees and not request.path.startswith(chemins_exclus):
                    return redirect('changer_mot_de_passe_agent')

            chef = getattr(request.user, 'chef', None)
            if chef and chef.doit_changer_mot_de_passe:
                urls_autorisees = [reverse('changer_mot_de_passe_chef'), reverse('logout')]
                chemins_exclus = ('/static/', '/media/')
                if request.path not in urls_autorisees and not request.path.startswith(chemins_exclus):
                    return redirect('changer_mot_de_passe_chef')

        return self.get_response(request)