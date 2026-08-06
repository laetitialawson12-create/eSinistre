from datetime import timedelta
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import logout
from django.utils import timezone


class InactiviteMiddleware:
    # Définition de la durée maximale d'inactivité autorisée
    DELAI_INACTIVITE = timedelta(minutes=30)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Vérifie si l'utilisateur est connecté
        if request.user.is_authenticated:
            # Récupère l'horodatage de la dernière activité stocké en session
            derniere_activite = request.session.get('derniere_activite')
            maintenant = timezone.now().timestamp()

            # Si une drnière activité existe et que le délai d'inactivité est dépassé
            if derniere_activite and (maintenant - derniere_activite) > self.DELAI_INACTIVITE.total_seconds():
                logout(request)
                return redirect('login')

            # Met à jour le timestamp de la dernière activité avec l'heure actuelle
            request.session['derniere_activite'] = maintenant

        return self.get_response(request)


class PolitiqueConfidentialiteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Vérifie si l'utilisateur est connecté
        if request.user.is_authenticated:
            # Récupère le profil 'assure' associé à l'utilisateur, s'il existe
            assure = getattr(request.user, 'assure', None)
            # Si l'utilisateur est un assuré et n'a pas encore accepté la politique
            if assure and not assure.politique_confidentialite_acceptee:
                # Liste des URLs autorisées malgré tout
                urls_autorisees = [
                    reverse('politique_confidentialite'),
                    reverse('logout'),
                ]
                # Chemins à exclure de la vérification (fichiers statiques et médias)
                chemins_exclus = ('/static/', '/media/')
                
                # Si l'URL demandée n'est ni autorisée ni dans les chemins exclus, on redirige
                if request.path not in urls_autorisees and not request.path.startswith(chemins_exclus):
                    return redirect('politique_confidentialite')

        return self.get_response(request)
    

class MotDePasseTemporaireMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Vérifie si l'utilisateur est connecté
        if request.user.is_authenticated:
            # Contrôle pour le profil 'agent'
            agent = getattr(request.user, 'agent', None)
            if agent and agent.doit_changer_mot_de_passe:
                urls_autorisees = [reverse('changer_mot_de_passe_agent'), reverse('logout')]
                chemins_exclus = ('/static/', '/media/')
                if request.path not in urls_autorisees and not request.path.startswith(chemins_exclus):
                    return redirect('changer_mot_de_passe_agent')

            # Contrôle pour le profil 'chef'
            chef = getattr(request.user, 'chef', None)
            if chef and chef.doit_changer_mot_de_passe:
                urls_autorisees = [reverse('changer_mot_de_passe_chef'), reverse('logout')]
                chemins_exclus = ('/static/', '/media/')
                if request.path not in urls_autorisees and not request.path.startswith(chemins_exclus):
                    return redirect('changer_mot_de_passe_chef')

        return self.get_response(request)