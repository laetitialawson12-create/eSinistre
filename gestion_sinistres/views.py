from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import SinistreForm, PieceJointeFormSet
from .models import Sinistre, PieceJointe

# --- PARCOURS ASSURÉ ---

@login_required
def declarer_sinistre(request):
    if request.method == 'POST':
        form = SinistreForm(request.POST, request.FILES, user=request.user)
        formset = PieceJointeFormSet(request.POST, request.FILES)
        
        if form.is_valid() and formset.is_valid():
            # Utilisation de commit=False pour injecter l'utilisateur
            sinistre = form.save(commit=False)
            sinistre.assure = request.user  # Assure le lien avec l'utilisateur
            sinistre.save()
            
            formset.instance = sinistre
            formset.save()
            
            request.session['temp_sinistre_id'] = sinistre.id
            return redirect('confirmer_sinistre')
    else:
        form = SinistreForm(user=request.user)
        formset = PieceJointeFormSet()
    return render(request, 'declaration.html', {'form': form, 'formset': formset})

@login_required
def confirmer_sinistre(request):
    sinistre_id = request.session.get('temp_sinistre_id')
    if not sinistre_id:
        return redirect('declarer_sinistre')
    sinistre = get_object_or_404(Sinistre, id=sinistre_id, assure=request.user)
    return render(request, 'confirmation.html', {'sinistre': sinistre})

@login_required
def finaliser_envoi(request):
    if request.method == 'POST':
        # Logique de changement de statut vers "En cours"
        if 'temp_sinistre_id' in request.session:
            del request.session['temp_sinistre_id']
        messages.success(request, 'Dossier transmis avec succès.')
        return redirect('accueil_assure')
    return redirect('confirmer_sinistre')

@login_required
def accueil_assure(request):
    # Filtrage strict par utilisateur connecté
    sinistres = Sinistre.objects.filter(assure=request.user)
    context = {
        'sinistres': sinistres,
        'total_en_cours': sinistres.filter(statut='en_cours').count(),
        'total_attente': sinistres.filter(statut='attente_complements').count(),
    }
    return render(request, 'accueil_assure.html', context)

@login_required
def detail_sinistre(request, sinistre_id):
    # Sécurise l'accès : l'utilisateur ne peut voir que SON dossier
    sinistre = get_object_or_404(Sinistre, id=sinistre_id, assure=request.user)
    return render(request, 'detail_sinistre.html', {'sinistre': sinistre})

@login_required
def suivi_sinistres(request):
    # On récupère uniquement les sinistres de l'utilisateur connecté
    sinistres = Sinistre.objects.filter(assure=request.user).order_by('-date_declaration')
    return render(request, 'suivi_sinistres.html', {'sinistres': sinistres})


# --- ESPACE AGENT (SQUELETTE) ---

@login_required
def tableau_bord_agent(request):
    # Vérification simple : nécessite un groupe 'Agent' (à implémenter)
    if not request.user.groups.filter(name='Agent').exists():
        return redirect('accueil_assure')
    
    sinistres_a_traiter = Sinistre.objects.filter(statut='en_cours')
    return render(request, 'agent/dashboard.html', {'sinistres': sinistres_a_traiter})


# Ajoutez cette fonction à votre fichier views.py actuel
@login_required
def documents_assure(request):
    # Récupère les pièces jointes liées aux véhicules de l'assuré connecté
    pieces = PieceJointe.objects.filter(sinistre__vehicule__proprietaire=request.user)
    # Récupère les sinistres ayant une lettre de dérogation pour cet assuré
    derogations = Sinistre.objects.filter(
        vehicule__proprietaire=request.user
    ).exclude(lettre_derogation__isnull=True).exclude(lettre_derogation='')
    
    return render(request, 'documents_assure.html', {'pieces': pieces, 'derogations': derogations})

# Ajoutez cette fonction à votre fichier views.py
@login_required
def profil_assure(request):
    return render(request, 'profil_assure.html', {'user': request.user})


def detail_sinistre(request, sinistre_id):
    sinistre = get_object_or_404(Sinistre, id=sinistre_id, assure=request.user)
    # On récupère l'historique trié par date
    historique = sinistre.historique.all().order_by('date_changement')
    # Pour les messages (si vous avez un modèle Message), sinon listez-les ici
    messages = sinistre.messages.all().order_by('date_envoi')
    
    return render(request, 'detail_sinistre.html', {
        'sinistre': sinistre,
        'historique': historique,
        'messages': messages,
    })