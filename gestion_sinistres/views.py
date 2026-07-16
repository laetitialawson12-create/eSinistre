from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import SinistreForm
from .models import Sinistre, PieceJointe, Message, HistoriqueSinistre, EtapeSinistre

@login_required
def declarer_sinistre(request):
    if request.method == 'POST':
        form = SinistreForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            sinistre = form.save(commit=False)
            sinistre.assure = request.user
            sinistre.save()
            
            # Sauvegarde des fichiers
            files = request.FILES.getlist('fichiers_justificatifs')
            for f in files:
                PieceJointe.objects.create(sinistre=sinistre, fichier=f)
            
            # Stockage en session pour la confirmation
            request.session['temp_sinistre_id'] = sinistre.id
            messages.success(request, f"Sinistre {sinistre.numero_sinistre} déclaré avec succès.")
            return redirect('confirmer_sinistre') 
    else:
        form = SinistreForm(user=request.user)
    
    return render(request, 'declaration.html', {'form': form})

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
        if 'temp_sinistre_id' in request.session:
            del request.session['temp_sinistre_id']
        messages.success(request, 'Dossier transmis avec succès.')
        return redirect('accueil_assure')
    return redirect('confirmer_sinistre')

@login_required
def accueil_assure(request):
    all_sinistres = Sinistre.objects.filter(assure=request.user)
    context = {
        'total': all_sinistres.count(),
        'en_cours': all_sinistres.filter(statut='EN_COURS').count(),
        'derniers': all_sinistres.order_by('-date_declaration')[:5],
    }
    return render(request, 'accueil_assure.html', context)

@login_required
def suivi_sinistres(request):
    sinistres = Sinistre.objects.filter(assure=request.user).order_by('-date_declaration')
    return render(request, 'suivi_sinistres.html', {'sinistres': sinistres})

@login_required
def detail_sinistre(request, sinistre_id):
    # Sécurisation : l'utilisateur ne peut voir que ses propres sinistres
    sinistre = get_object_or_404(Sinistre, id=sinistre_id, assure=request.user)
    
    # Gestion de l'envoi de message en POST
    if request.method == 'POST' and 'contenu' in request.POST:
        Message.objects.create(
            sinistre=sinistre,
            auteur=request.user,
            contenu=request.POST.get('contenu')
        )
        return redirect('detail_sinistre', sinistre_id=sinistre.id)

    # Contexte pour le rendu
    context = {
        'sinistre': sinistre,
        'historique': sinistre.historique.all().order_by('date_changement'),
        'messages': sinistre.messages.all().order_by('date_envoi'),
        'documents': sinistre.pieces.all(),
    }
    return render(request, 'detail_sinistre.html', context)


@login_required
def tableau_bord_agent(request):
    # Vérification simple pour l'accès agent
    if not request.user.groups.filter(name='Agent').exists():
        return redirect('accueil_assure')
    
    sinistres_a_traiter = Sinistre.objects.filter(statut='EN_COURS')
    return render(request, 'agent/dashboard.html', {'sinistres': sinistres_a_traiter})

@login_required
def documents_assure(request):
    pieces = PieceJointe.objects.filter(sinistre__assure=request.user)
    return render(request, 'documents_assure.html', {'pieces': pieces})

@login_required
def profil_assure(request):
    return render(request, 'profil_assure.html', {'user': request.user})