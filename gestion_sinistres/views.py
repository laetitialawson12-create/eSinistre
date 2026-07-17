from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import SinistreForm, ModifierProfilForm, AgentCreationForm
from .models import Sinistre, PieceJointe, Message, HistoriqueSinistre, EtapeSinistre, Assure, Agent
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.utils import timezone


@login_required
def redirection_login(request):
    if hasattr(request.user, 'agent'):
        return redirect('accueil_agent')
    if hasattr(request.user, 'assure'):
        return redirect('accueil_assure')
    return redirect('login')


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


@login_required
def accueil_agent(request):
    agent = getattr(request.user, 'agent', None)
    if not agent:
        return redirect('accueil_assure')

    sinistres_agence = Sinistre.objects.all()

    context = {
        'agent': agent,
        'a_instruire': sinistres_agence.filter(statut='SOUMIS').count(),
        'attente_complements': sinistres_agence.filter(statut='ATTENTE_COMPLEMENTS').count(),
        'valides_ce_mois': sinistres_agence.filter(
            statut='CLOTURE',
            date_declaration__month=timezone.now().month,
            date_declaration__year=timezone.now().year,
        ).count(),
        'derniers_a_instruire': sinistres_agence.filter(statut='SOUMIS').order_by('-date_declaration')[:5],
    }
    return render(request, 'accueil_agent.html', context)



@login_required
def changer_mot_de_passe_agent(request):
    agent = getattr(request.user, 'agent', None)
    if not agent:
        return redirect('accueil_assure')

    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)  # évite d'être déconnecté
            agent.doit_changer_mot_de_passe = False
            agent.compte_active = True
            agent.save()
            messages.success(request, "Mot de passe modifié avec succès.")
            return redirect('accueil_agent')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'changer_mot_de_passe_agent.html', {'form': form})


@login_required
@user_passes_test(lambda u: u.is_staff)
def creer_agent(request):
    if request.method == 'POST':
        form = AgentCreationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            username = f"{data['prenom']}.{data['nom']}".lower().replace(' ', '')

            user = User.objects.create_user(
                username=username,
                email=data['email'],
                first_name=data['prenom'],
                last_name=data['nom'],
            )
            user.set_password('0000')  # mot de passe par défaut, bypass des validateurs
            user.save()

            Agent.objects.create(
                user=user,
                agence=data['agence'],
                matricule=data['matricule'],
                telephone=data['telephone'],
                compte_active=False,
                doit_changer_mot_de_passe=True,
            )
            messages.success(request, f"Agent créé. Identifiant : {username} — Mot de passe temporaire : 0000")
            return redirect('creer_agent')
    else:
        form = AgentCreationForm()

    return render(request, 'creer_agent.html', {'form': form})


@login_required
def dossiers_a_instruire(request):
    agent = getattr(request.user, 'agent', None)
    if not agent:
        return redirect('accueil_assure')

    sinistres = Sinistre.objects.filter(
        statut__in=['SOUMIS', 'ATTENTE_COMPLEMENTS', 'A_CORRIGER']
    ).order_by('date_declaration')

    return render(request, 'agent_a_instruire.html', {'agent': agent, 'sinistres': sinistres})


@login_required
def prendre_en_charge(request, sinistre_id):
    agent = getattr(request.user, 'agent', None)
    if not agent:
        return redirect('accueil_assure')

    sinistre = get_object_or_404(Sinistre, id=sinistre_id)

    if sinistre.statut == 'SOUMIS':
        sinistre.statut = 'EN_COURS'
        sinistre.agent_traitant = request.user.get_full_name() or request.user.username
        sinistre.save()
        HistoriqueSinistre.objects.create(
            sinistre=sinistre,
            statut='EN_COURS',
            commentaires="Dossier pris en charge par l'agent.",
            auteur=request.user,
        )
        messages.success(request, f"Dossier {sinistre.numero_sinistre} pris en charge.")

    return redirect('detail_sinistre_agent', sinistre_id=sinistre.id)


@login_required
def detail_sinistre_agent(request, sinistre_id):
    agent = getattr(request.user, 'agent', None)
    if not agent:
        return redirect('accueil_assure')

    sinistre = get_object_or_404(Sinistre, id=sinistre_id)

    if request.method == 'POST' and 'contenu' in request.POST:
        Message.objects.create(sinistre=sinistre, auteur=request.user, contenu=request.POST.get('contenu'))
        return redirect('detail_sinistre_agent', sinistre_id=sinistre.id)

    context = {
        'agent': agent,
        'sinistre': sinistre,
        'historique': sinistre.historique.all().order_by('date_changement'),
        'discussion': sinistre.messages.all().order_by('date_envoi'),
        'documents': sinistre.pieces.all(),
    }
    return render(request, 'detail_sinistre_agent.html', context)