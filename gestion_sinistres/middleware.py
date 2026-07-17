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