from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import SinistreForm, PieceJointeFormSet
from .models import Sinistre, PieceJointe
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView

@login_required
def declarer_sinistre(request):
    if request.method == 'POST':
        form = SinistreForm(request.POST, request.FILES)
        formset = PieceJointeFormSet(request.POST, request.FILES)
        
        if form.is_valid() and formset.is_valid():
            # 1. Sauvegarder le sinistre mais ne pas valider tout de suite en base (commit=False)
            sinistre = form.save()
            
            # 2. Lier les pièces jointes au sinistre et les sauvegarder
            formset.instance = sinistre
            formset.save()
            
            # 3. Stocker l'ID dans la session pour le retrouver à l'étape de confirmation
            request.session['temp_sinistre_id'] = sinistre.id
            
            messages.success(request, 'Votre déclaration a été enregistrée. Veuillez vérifier les informations.')
            return redirect('confirmer_sinistre')
        else:
            messages.error(request, 'Veuillez corriger les erreurs dans le formulaire.')
    else:
        form = SinistreForm()
        formset = PieceJointeFormSet()
        
    return render(request, 'declaration.html', {'form': form, 'formset': formset})

def confirmer_sinistre(request):
    # Récupérer l'ID de la session
    sinistre_id = request.session.get('temp_sinistre_id')
    if not sinistre_id:
        return redirect('declarer_sinistre')
    
    sinistre = Sinistre.objects.get(id=sinistre_id)
    # Récupérer les pièces jointes liées pour les afficher
    pieces = sinistre.pieces.all()
    
    return render(request, 'confirmation.html', {'sinistre': sinistre, 'pieces': pieces})

def finaliser_envoi(request):
    if request.method == 'POST':
        # Ici, vous pourriez changer un statut (ex: brouillon -> soumis)
        # Supprimer la donnée de session après finalisation
        if 'temp_sinistre_id' in request.session:
            del request.session['temp_sinistre_id']
        
        messages.success(request, 'Votre dossier a été transmis avec succès à Fidelia.')
        return redirect('declarer_sinistre') # Ou vers une page "Merci"
    
    return redirect('confirmer_sinistre')

@login_required
def accueil_assure(request):
    sinistres = Sinistre.objects.filter(vehicule__proprietaire=request.user)
    context = {
        'total': sinistres.count(),
        'en_cours': sinistres.exclude(statut__in=['CLOTURE', 'SANS_SUITE']).count(),
        'derniers': sinistres.order_by('-date_declaration')[:5],
    }
    return render(request, 'accueil_assure.html', context)


@login_required
def suivi_sinistres(request):
    sinistres = Sinistre.objects.filter(vehicule__proprietaire=request.user).order_by('-date_declaration')
    return render(request, 'suivi_sinistres.html', {'sinistres':sinistres})


@login_required
def documents_assure(request):
    pieces = PieceJointe.objects.filter(sinistre__vehicule__proprietaire=request.user)
    derogations = Sinistre.objects.filter(
        vehicule__proprietaire=request.user
    ).exclude(lettre_derogation='').exclude(lettre_derogation__isnull=True)
    return render(request, 'documents_assure.html', {'pieces': pieces, 'derogations': derogations})


@login_required
def profil_assure(request):
    return render(request, 'profil_assure.html', {'user': request.user})