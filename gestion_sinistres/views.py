from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import SinistreForm, ModifierProfilForm
from .models import Sinistre, PieceJointe, Message, HistoriqueSinistre, EtapeSinistre, Assure
from django.contrib.auth import login
from django.contrib.auth.forms import SetPasswordForm


@login_required
def declarer_sinistre(request):
    sinistre_id = request.session.get('temp_sinistre_id')
    instance = None
    if sinistre_id:
        instance = Sinistre.objects.filter(id=sinistre_id, assure=request.user).first()

    if request.method == 'POST':
        form = SinistreForm(request.POST, request.FILES, user=request.user, instance=instance)
        if form.is_valid():
            sinistre = form.save(commit=False)
            sinistre.assure = request.user
            sinistre.save()

            # Sauvegarde des fichiers
            files = request.FILES.getlist('fichiers_justificatifs')
            for f in files:
                PieceJointe.objects.create(sinistre=sinistre, fichier=f)

            request.session['temp_sinistre_id'] = sinistre.id
            messages.success(request, f"Sinistre {sinistre.numero_sinistre} déclaré avec succès.")
            return redirect('confirmer_sinistre')
    else:
        form = SinistreForm(user=request.user, instance=instance)

    return render(request, 'declaration.html', {'form': form})

@login_required
def annuler_declaration(request):
    sinistre_id = request.session.pop('temp_sinistre_id', None)
    if sinistre_id:
        Sinistre.objects.filter(id=sinistre_id, assure=request.user).delete()
    return redirect('accueil_assure')


@login_required
def confirmer_sinistre(request):
    sinistre_id = request.session.get('temp_sinistre_id')
    if not sinistre_id:
        return redirect('declarer_sinistre')
    sinistre = get_object_or_404(Sinistre, id=sinistre_id, assure=request.user)
    pieces = sinistre.pieces.all()
    return render(request, 'confirmation.html', {'sinistre': sinistre, 'pieces': pieces})


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
        'discussion': sinistre.messages.all().order_by('date_envoi'),
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

@login_required
def modifier_profil(request):
    if request.method == 'POST':
        form = ModifierProfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Vos informations ont été mises à jour.")
            return redirect('profil_assure')
    else:
        form = ModifierProfilForm(instance=request.user)
    return render(request, 'modifier_profil.html', {'form': form})


def activation_etape1(request):
    if request.method == 'POST':
        numero_police = request.POST.get('numero_police', '').strip()
        assure = Assure.objects.filter(numero_police=numero_police, compte_active=False).first()
        if assure:
            request.session['activation_assure_id'] = assure.id
            return redirect('activation_etape2')
        else:
            messages.error(request, "Numéro de police introuvable ou compte déjà activé.")
    return render(request, 'activation_etape1.html')


def activation_etape2(request):
    assure_id = request.session.get('activation_assure_id')
    if not assure_id:
        return redirect('activation_etape1')
    assure = get_object_or_404(Assure, id=assure_id, compte_active=False)

    if request.method == 'POST':
        form = SetPasswordForm(assure.user, request.POST)
        if form.is_valid():
            form.save()
            assure.compte_active = True
            assure.save()
            del request.session['activation_assure_id']
            login(request, assure.user)
            return redirect('politique_confidentialite')
    else:
        form = SetPasswordForm(assure.user)

    return render(request, 'activation_etape2.html', {'form': form, 'assure': assure})


@login_required
def politique_confidentialite(request):
    assure = getattr(request.user, 'assure', None)
    if not assure:
        return redirect('accueil_assure')

    if assure.politique_confidentialite_acceptee:
        return redirect('accueil_assure')

    if request.method == 'POST':
        assure.politique_confidentialite_acceptee = True
        assure.save()
        return redirect('accueil_assure')

    return render(request, 'politique_confidentialite.html')