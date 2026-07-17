from django.shortcuts import redirect
from django.urls import reverse


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
                urls_autorisees = [
                    reverse('changer_mot_de_passe_agent'),
                    reverse('logout'),
                ]
                chemins_exclus = ('/static/', '/media/')
                if request.path not in urls_autorisees and not request.path.startswith(chemins_exclus):
                    return redirect('changer_mot_de_passe_agent')

        return self.get_response(request)