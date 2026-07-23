import os
import pandas as pd
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
from django.urls import reverse

from .forms import (
    SinistreForm, ModifierProfilForm, AgentCreationForm, AssureAdminForm,
    DemanderComplementsForm, MarquerConformeForm, IndemnisationForm,
    ChefCreationForm, ModifierAgentAdminForm, ModifierChefAdminForm,
    ImportExcelForm, SansSuiteForm
)
from .models import (
    Sinistre, PieceJointe, Message, HistoriqueSinistre, EtapeSinistre,
    Assure, Agent, Agence, ChefDepartement, Quittance, Vehicule
)


# --- AUTHENTIFICATION & REDIRECTION ---

@login_required
def redirection_login(request):
    if request.user.is_staff:
        return redirect('accueil_admin')
    if hasattr(request.user, 'chef'):
        return redirect('accueil_chef')
    if hasattr(request.user, 'agent'):
        return redirect('accueil_agent')
    if hasattr(request.user, 'assure'):
        return redirect('accueil_assure')
    return redirect('login')


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
            assure.user.is_active = True
            assure.user.save()
            assure.compte_active = True
            assure.save()
            del request.session['activation_assure_id']
            login(request, assure.user, backend='django.contrib.auth.backends.ModelBackend')
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


# --- ESPACE ASSURÉ ---

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
def declarer_sinistre(request):
    if request.method == 'POST':
        form = SinistreForm(request.POST, request.FILES, user=request.user)
        
        if form.is_valid():
            sinistre = form.save(commit=False)
            sinistre.assure = request.user
            
            # Attributions automatiques de la quittance
            date_evenement = sinistre.date_survenance
            vehicule = sinistre.vehicule
            contrat = getattr(vehicule, 'contrat', None)

            if contrat and date_evenement:
                quittances_valides = Quittance.objects.filter(
                    contrat=contrat,
                    date_debut__lte=date_evenement,
                    date_fin__gte=date_evenement
                )
                if quittances_valides.count() == 1:
                    sinistre.quittance = quittances_valides.first()
                else:
                    sinistre.quittance = None
            else:
                sinistre.quittance = None

            try:
                sinistre.save()

                fichiers = request.FILES.getlist('fichiers_justificatifs')
                for f in fichiers:
                    PieceJointe.objects.create(sinistre=sinistre, fichier=f)

                if sinistre.quittance:
                    messages.success(request, f"Votre sinistre N° {sinistre.numero_sinistre} a été enregistré avec succès.")
                else:
                    messages.info(
                        request, 
                        f"Votre sinistre N° {sinistre.numero_sinistre} a été enregistré. "
                        "Une vérification de la quittance par un agent est requise."
                    )

                return redirect('detail_sinistre', sinistre_id=sinistre.id)

            except ValidationError as e:
                form.add_error(None, e)
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = SinistreForm(user=request.user)

    return render(request, 'eSinistre/declarer_sinistre.html', {'form': form, 'title': 'Déclarer un sinistre'})


@login_required
def detail_sinistre(request, sinistre_id):
    """Vue permettant à l'assuré de consulter son dossier."""
    sinistre = get_object_or_404(Sinistre, id=sinistre_id, assure=request.user)
    
    if request.method == 'POST' and 'contenu' in request.POST:
        Message.objects.create(
            sinistre=sinistre,
            auteur=request.user,
            contenu=request.POST.get('contenu')
        )
        messages.success(request, "Message envoyé avec succès.")
        return redirect('detail_sinistre', sinistre_id=sinistre.id)

    context = {
        'sinistre': sinistre,
        'documents': sinistre.pieces.all(),
        'historique': sinistre.historique.all().order_by('-date_changement'),
        'discussion': sinistre.messages.all().order_by('date_envoi'),
    }
    return render(request, 'eSinistre/detail_sinistre.html', context)


@login_required
def suivi_sinistres(request):
    sinistres = Sinistre.objects.filter(assure=request.user).order_by('-date_declaration')
    return render(request, 'suivi_sinistres.html', {'sinistres': sinistres})


@login_required
def fournir_complements(request, sinistre_id):
    sinistre = get_object_or_404(Sinistre, id=sinistre_id, assure=request.user)

    if sinistre.statut != 'ATTENTE_COMPLEMENTS':
        messages.error(request, "Ce dossier ne requiert pas de compléments actuellement.")
        return redirect('suivi_sinistres')

    if request.method == 'POST':
        sinistre.precision = request.POST.get('precisions')
        if request.FILES.get('document'):
            sinistre.lettre_derogation = request.FILES['document']
        sinistre.statut = 'SOUMIS'
        sinistre.save()

        messages.success(request, f"Vos compléments pour le dossier {sinistre.numero_sinistre} ont été transmis.")
        return redirect('suivi_sinistres')

    return render(request, 'fournir_complements.html', {'sinistre': sinistre})


@login_required
def annuler_declaration(request):
    sinistre_id = request.session.pop('temp_sinistre_id', None)
    if sinistre_id:
        Sinistre.objects.filter(id=sinistre_id, assure=request.user).delete()
    return redirect('accueil_assure')


@login_required
def confirmer_sinistre(request):
    sinistre_id = request.session.get('temp_sinistre_id')
    sinistre = Sinistre.objects.filter(id=sinistre_id, assure=request.user).first() if sinistre_id else None

    if not sinistre:
        request.session.pop('temp_sinistre_id', None)
        messages.error(request, "Aucune déclaration en cours. Merci de recommencer.")
        return redirect('declarer_sinistre')

    return render(request, 'confirmation.html', {'sinistre': sinistre, 'pieces': sinistre.pieces.all()})


@login_required
def finaliser_envoi(request):
    if request.method == 'POST':
        sinistre_id = request.session.get('temp_sinistre_id')
        sinistre = get_object_or_404(Sinistre, id=sinistre_id, assure=request.user) if sinistre_id else None

        if 'temp_sinistre_id' in request.session:
            del request.session['temp_sinistre_id']

        if sinistre:
            messages.success(request, f"Votre sinistre {sinistre.numero_sinistre} a été déclaré avec succès.")
        return redirect('accueil_assure')
    return redirect('confirmer_sinistre')


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


@login_required
def mes_contrats(request):
    quittances = Quittance.objects.filter(contrat__user=request.user).prefetch_related('vehicules')
    return render(request, 'mes_contrats.html', {'quittances': quittances})


# --- ESPACE AGENT ---

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
def tableau_bord_agent(request):
    if not request.user.groups.filter(name='Agent').exists():
        return redirect('accueil_assure')
    sinistres_a_traiter = Sinistre.objects.filter(statut='EN_COURS')
    return render(request, 'agent/dashboard.html', {'sinistres': sinistres_a_traiter})


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

    if sinistre.statut == 'SOUMIS' and not sinistre.agent_traitant:
        sinistre.agent_traitant = request.user.get_full_name() or request.user.username
        sinistre.save()
        HistoriqueSinistre.objects.create(
            sinistre=sinistre,
            statut=sinistre.statut,
            commentaires="Dossier pris en charge par l'agent pour vérification.",
            auteur=request.user,
        )
        messages.success(request, f"Dossier {sinistre.numero_sinistre} pris en charge.")

    return redirect('detail_sinistre_agent', sinistre_id=sinistre.id)


@login_required
def detail_sinistre_agent(request, sinistre_id):
    """Vue détaillée pour les agents de gestion."""
    agent = getattr(request.user, 'agent', None)
    if not agent:
        return redirect('accueil_assure')

    sinistre = get_object_or_404(Sinistre, id=sinistre_id)
    assure_profile = getattr(sinistre.assure, 'assure', None)

    # Récupération des quittances éligibles
    quittances_disponibles = Quittance.objects.none()
    if assure_profile and sinistre.date_survenance:
        date_ref = sinistre.date_survenance.date() if hasattr(sinistre.date_survenance, 'date') else sinistre.date_survenance
        quittances_disponibles = Quittance.objects.filter(
            contrat=assure_profile,
            date_debut__lte=date_ref,
            date_fin__gte=date_ref,
        ).order_by('-date_debut')

    # Message direct à l'assuré
    if request.method == 'POST' and 'contenu' in request.POST:
        Message.objects.create(sinistre=sinistre, auteur=request.user, contenu=request.POST.get('contenu'))
        messages.success(request, "Message transmis.")
        return redirect('detail_sinistre_agent', sinistre_id=sinistre.id)

    context = {
        'agent': agent,
        'sinistre': sinistre,
        'historique': sinistre.historique.all().order_by('date_changement'),
        'discussion': sinistre.messages.all().order_by('date_envoi'),
        'documents': sinistre.pieces.all(),
        'quittances_disponibles': quittances_disponibles,
    }
    return render(request, 'detail_sinistre_agent.html', context)


@login_required
def lier_quittance_agent(request, sinistre_id):
    agent = getattr(request.user, 'agent', None)
    if not agent:
        return redirect('accueil_assure')

    sinistre = get_object_or_404(Sinistre, id=sinistre_id)

    if request.method == 'POST':
        quittance_id = request.POST.get('quittance_id')
        if quittance_id:
            assure_profile = getattr(sinistre.assure, 'assure', None)
            quittance = get_object_or_404(Quittance, id=quittance_id, contrat=assure_profile)
            sinistre.quittance = quittance
            try:
                sinistre.save()
                messages.success(request, f"La quittance N° {quittance.numero_quittance} a été liée au sinistre.")
            except ValidationError as e:
                messages.error(request, f"Impossible de lier cette quittance : {e}")
        else:
            messages.warning(request, "Veuillez sélectionner une quittance valide.")

    return redirect('detail_sinistre_agent', sinistre_id=sinistre.id)


@login_required
def marquer_conforme(request, sinistre_id):
    agent = getattr(request.user, 'agent', None)
    if not agent:
        return redirect('accueil_assure')

    sinistre = get_object_or_404(Sinistre, id=sinistre_id)

    if sinistre.statut in ('SOUMIS', 'A_CORRIGER'):
        sinistre.statut = 'ATTENTE_VALIDATION'
        sinistre.save()
        HistoriqueSinistre.objects.create(
            sinistre=sinistre,
            statut='ATTENTE_VALIDATION',
            commentaires="Dossier jugé conforme (première validation), transmis au Chef de département.",
            auteur=request.user,
        )
        messages.success(request, f"Dossier {sinistre.numero_sinistre} envoyé au Chef pour validation.")

    return redirect('detail_sinistre_agent', sinistre_id=sinistre.id)


@login_required
def demander_complements(request, sinistre_id):
    agent = getattr(request.user, 'agent', None)
    if not agent:
        return redirect('accueil_assure')

    sinistre = get_object_or_404(Sinistre, id=sinistre_id)

    if request.method == 'POST':
        form = DemanderComplementsForm(request.POST)
        if form.is_valid():
            sinistre.statut = 'ATTENTE_COMPLEMENTS'
            sinistre.save()
            motif = form.cleaned_data['motif']
            Message.objects.create(sinistre=sinistre, auteur=request.user, contenu=motif)
            HistoriqueSinistre.objects.create(
                sinistre=sinistre,
                statut='ATTENTE_COMPLEMENTS',
                commentaires=motif,
                auteur=request.user,
            )
            messages.success(request, f"Demande de compléments envoyée pour le dossier {sinistre.numero_sinistre}.")
            return redirect('detail_sinistre_agent', sinistre_id=sinistre.id)
    else:
        form = DemanderComplementsForm()

    return render(request, 'demander_complements.html', {'sinistre': sinistre, 'form': form})


@login_required
def saisir_prix_retenu(request, sinistre_id):
    agent = getattr(request.user, 'agent', None)
    if not agent:
        return redirect('accueil_assure')

    sinistre = get_object_or_404(Sinistre, id=sinistre_id, statut='EN_COURS')

    if request.method == 'POST':
        form = MarquerConformeForm(request.POST)
        if form.is_valid():
            sinistre.prix_retenu = form.cleaned_data['prix_retenu']
            try:
                sinistre.save()
                HistoriqueSinistre.objects.create(
                    sinistre=sinistre,
                    statut='EN_COURS',
                    commentaires=f"Prix retenu saisi : {sinistre.prix_retenu} FCFA.",
                    auteur=request.user,
                )
                messages.success(request, "Prix retenu enregistré.")
            except ValidationError as e:
                messages.error(request, f"Erreur : {e}")

    return redirect('detail_sinistre_agent', sinistre_id=sinistre.id)


@login_required
def saisir_indemnisation(request, sinistre_id):
    agent = getattr(request.user, 'agent', None)
    if not agent:
        return redirect('accueil_assure')

    sinistre = get_object_or_404(Sinistre, id=sinistre_id, statut='CLOTURE')

    if request.method == 'POST':
        form = IndemnisationForm(request.POST)
        if form.is_valid():
            for champ, valeur in form.cleaned_data.items():
                setattr(sinistre, champ, valeur)
            sinistre.save()
            HistoriqueSinistre.objects.create(
                sinistre=sinistre,
                statut='CLOTURE',
                commentaires=(
                    f"Chèque n°{sinistre.numero_cheque} ({sinistre.banque_cheque}) remis à "
                    f"{sinistre.beneficiaire_nom} {sinistre.beneficiaire_prenoms} "
                    f"({sinistre.beneficiaire_telephone})."
                ),
                auteur=request.user,
            )
            messages.success(request, "Informations d'indemnisation enregistrées.")
            return redirect('detail_sinistre_agent', sinistre_id=sinistre.id)
    else:
        form = IndemnisationForm()

    return render(request, 'saisir_indemnisation.html', {'sinistre': sinistre, 'form': form})


@login_required
def dossiers_en_cours(request):
    agent = getattr(request.user, 'agent', None)
    if not agent:
        return redirect('accueil_assure')
    sinistres = Sinistre.objects.filter(statut='EN_COURS').order_by('-date_declaration')
    return render(request, 'dossiers_en_cours.html', {'agent': agent, 'sinistres': sinistres})


@login_required
def dossiers_clotures(request):
    agent = getattr(request.user, 'agent', None)
    if not agent:
        return redirect('accueil_assure')
    sinistres = Sinistre.objects.filter(statut__in=['CLOTURE', 'SANS_SUITE']).order_by('-date_declaration')
    return render(request, 'dossiers_clotures.html', {'agent': agent, 'sinistres': sinistres})


@login_required
def changer_mot_de_passe_agent(request):
    agent = getattr(request.user, 'agent', None)
    if not agent:
        return redirect('accueil_assure')

    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            agent.doit_changer_mot_de_passe = False
            agent.compte_active = True
            agent.save()
            messages.success(request, "Mot de passe modifié avec succès.")
            return redirect('accueil_agent')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'changer_mot_de_passe_agent.html', {'form': form})


@login_required
def profil_agent(request):
    agent = getattr(request.user, 'agent', None)
    if not agent:
        return redirect('accueil_assure')
    return render(request, 'profil_agent.html', {'agent': agent})


@login_required
def modifier_profil_agent(request):
    agent = getattr(request.user, 'agent', None)
    if not agent:
        return redirect('accueil_assure')
    if request.method == 'POST':
        form = ModifierProfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Vos informations ont été mises à jour.")
            return redirect('profil_agent')
    else:
        form = ModifierProfilForm(instance=request.user)
    return render(request, 'modifier_profil_agent.html', {'form': form})


# --- ESPACE CHEF DE DÉPARTEMENT ---

@login_required
def accueil_chef(request):
    chef = getattr(request.user, 'chef', None)
    if not chef:
        return redirect('accueil_assure')

    sinistres = Sinistre.objects.all()
    context = {
        'chef': chef,
        'a_valider': sinistres.filter(statut='ATTENTE_VALIDATION').count(),
        'en_cours': sinistres.filter(statut='EN_COURS').count(),
        'clotures_ce_mois': sinistres.filter(
            statut='CLOTURE',
            date_declaration__month=timezone.now().month,
            date_declaration__year=timezone.now().year,
        ).count(),
        'derniers_a_valider': sinistres.filter(statut='ATTENTE_VALIDATION').order_by('-date_declaration')[:5],
    }
    return render(request, 'accueil_chef.html', context)


@login_required
def dossiers_a_valider(request):
    chef = getattr(request.user, 'chef', None)
    if not chef:
        return redirect('accueil_assure')
    sinistres = Sinistre.objects.filter(statut='ATTENTE_VALIDATION').order_by('date_declaration')
    return render(request, 'dossiers_a_valider.html', {'chef': chef, 'sinistres': sinistres})


@login_required
def detail_sinistre_chef(request, sinistre_id):
    chef = getattr(request.user, 'chef', None)
    if not chef:
        return redirect('accueil_assure')

    sinistre = get_object_or_404(Sinistre, id=sinistre_id)

    if request.method == 'POST' and 'contenu' in request.POST:
        Message.objects.create(sinistre=sinistre, auteur=request.user, contenu=request.POST.get('contenu'))
        return redirect('detail_sinistre_chef', sinistre_id=sinistre.id)

    context = {
        'chef': chef,
        'sinistre': sinistre,
        'historique': sinistre.historique.all().order_by('date_changement'),
        'discussion': sinistre.messages.all().order_by('date_envoi'),
        'documents': sinistre.pieces.all(),
    }
    return render(request, 'detail_sinistre_chef.html', context)


@login_required
def valider_declaration(request, sinistre_id):
    chef = getattr(request.user, 'chef', None)
    if not chef:
        return redirect('accueil_assure')

    sinistre = get_object_or_404(Sinistre, id=sinistre_id, statut='ATTENTE_VALIDATION')
    sinistre.statut = 'EN_COURS'
    sinistre.attestation_generee = True
    sinistre.date_attestation = timezone.now()
    sinistre.save()

    HistoriqueSinistre.objects.create(
        sinistre=sinistre,
        statut='EN_COURS',
        commentaires="Déclaration validée par le Chef de département. Attestation générée et envoyée à l'assuré.",
        auteur=request.user,
    )
    messages.success(request, f"Dossier {sinistre.numero_sinistre} validé, attestation générée.")
    return redirect('detail_sinistre_chef', sinistre_id=sinistre.id)


@login_required
def renvoyer_a_agent(request, sinistre_id):
    chef = getattr(request.user, 'chef', None)
    if not chef:
        return redirect('accueil_assure')

    # Autorise le renvoi depuis les statuts 'ATTENTE_VALIDATION' et 'EN_COURS'
    sinistre = get_object_or_404(Sinistre, id=sinistre_id, statut__in=['ATTENTE_VALIDATION', 'EN_COURS'])

    if request.method == 'POST':
        # Récupère le motif depuis le champ 'commentaires' ou 'motif'
        commentaires = request.POST.get('commentaires') or request.POST.get('motif') or "Demande de révision."

        # Passages des statuts
        sinistre.statut = 'A_CORRIGER'
        sinistre.indemnisation_validee = False
        sinistre.save()

        # Inscription dans l'historique
        HistoriqueSinistre.objects.create(
            sinistre=sinistre,
            statut='A_CORRIGER',
            commentaires=commentaires,
            auteur=request.user,
        )

        messages.warning(request, f"Le dossier {sinistre.numero_sinistre} a été renvoyé à l'agent pour révision.")
        return redirect('detail_sinistre_chef', sinistre_id=sinistre.id)

    return redirect('detail_sinistre_chef', sinistre_id=sinistre.id)


@login_required
def valider_indemnisation(request, sinistre_id):
    chef = getattr(request.user, 'chef', None)
    if not chef:
        return redirect('accueil_assure')

    sinistre = get_object_or_404(Sinistre, id=sinistre_id, statut='EN_COURS')

    if sinistre.prix_retenu is None:
        messages.error(request, "L'agent doit d'abord saisir le prix retenu.")
        return redirect('detail_sinistre_chef', sinistre_id=sinistre.id)

    sinistre.indemnisation_validee = True
    sinistre.save()
    HistoriqueSinistre.objects.create(
        sinistre=sinistre,
        statut='EN_COURS',
        commentaires=f"Indemnisation de {sinistre.prix_retenu} FCFA validée par le Chef de département.",
        auteur=request.user,
    )
    messages.success(request, "Indemnisation validée. Le dossier peut maintenant être clôturé ou classé sans suite.")
    return redirect('detail_sinistre_chef', sinistre_id=sinistre.id)


@login_required
def clore_sinistre(request, sinistre_id):
    chef = getattr(request.user, 'chef', None)
    if not chef:
        return redirect('accueil_assure')

    sinistre = get_object_or_404(Sinistre, id=sinistre_id, statut='EN_COURS')
    sinistre.statut = 'CLOTURE'
    sinistre.save()
    HistoriqueSinistre.objects.create(
        sinistre=sinistre,
        statut='CLOTURE',
        commentaires="Flux financiers constatés, dossier clôturé par le Chef de département.",
        auteur=request.user,
    )
    messages.success(request, f"Dossier {sinistre.numero_sinistre} clôturé.")
    return redirect('detail_sinistre_chef', sinistre_id=sinistre.id)


@login_required
def classer_sans_suite(request, sinistre_id):
    chef = getattr(request.user, 'chef', None)
    if not chef:
        return redirect('accueil_assure')

    sinistre = get_object_or_404(Sinistre, id=sinistre_id, statut='EN_COURS')

    if request.method == 'POST':
        form = SansSuiteForm(request.POST)
        if form.is_valid():
            sinistre.statut = 'SANS_SUITE'
            sinistre.motif_sans_suite = form.cleaned_data['motif']
            sinistre.save()
            HistoriqueSinistre.objects.create(
                sinistre=sinistre,
                statut='SANS_SUITE',
                commentaires=form.cleaned_data['motif'],
                auteur=request.user,
            )
            messages.success(request, f"Dossier {sinistre.numero_sinistre} classé sans suite.")
            return redirect('detail_sinistre_chef', sinistre_id=sinistre.id)
    else:
        form = SansSuiteForm()

    return render(request, 'classer_sans_suite.html', {'sinistre': sinistre, 'form': form})


@login_required
def reouvrir_dossier(request, sinistre_id):
    chef = getattr(request.user, 'chef', None)
    if not chef:
        return redirect('accueil_assure')

    sinistre = get_object_or_404(Sinistre, id=sinistre_id, statut__in=['CLOTURE', 'SANS_SUITE'])
    sinistre.statut = 'REOUVERT'
    sinistre.save()
    HistoriqueSinistre.objects.create(
        sinistre=sinistre,
        statut='REOUVERT',
        commentaires="Dossier réouvert par le Chef de département pour ré-instruction.",
        auteur=request.user,
    )
    messages.success(request, f"Dossier {sinistre.numero_sinistre} réouvert.")
    return redirect('detail_sinistre_chef', sinistre_id=sinistre.id)


@login_required
def dossiers_en_cours_chef(request):
    chef = getattr(request.user, 'chef', None)
    if not chef:
        return redirect('accueil_assure')
    sinistres = Sinistre.objects.filter(statut='EN_COURS').order_by('-date_declaration')
    return render(request, 'dossiers_en_cours_chef.html', {'chef': chef, 'sinistres': sinistres})


@login_required
def dossiers_clotures_chef(request):
    chef = getattr(request.user, 'chef', None)
    if not chef:
        return redirect('accueil_assure')
    sinistres = Sinistre.objects.filter(statut__in=['CLOTURE', 'SANS_SUITE']).order_by('-date_declaration')
    return render(request, 'dossiers_clotures_chef.html', {'chef': chef, 'sinistres': sinistres})


@login_required
def changer_mot_de_passe_chef(request):
    chef = getattr(request.user, 'chef', None)
    if not chef:
        return redirect('accueil_assure')

    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            chef.doit_changer_mot_de_passe = False
            chef.save()
            messages.success(request, "Mot de passe modifié avec succès.")
            return redirect('accueil_chef')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'changer_mot_de_passe_chef.html', {'form': form})


@login_required
def profil_chef(request):
    chef = getattr(request.user, 'chef', None)
    if not chef:
        return redirect('accueil_assure')
    return render(request, 'profil_chef.html', {'chef': chef})


@login_required
def modifier_profil_chef(request):
    chef = getattr(request.user, 'chef', None)
    if not chef:
        return redirect('accueil_assure')
    if request.method == 'POST':
        form = ModifierProfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Vos informations ont été mises à jour.")
            return redirect('profil_chef')
    else:
        form = ModifierProfilForm(instance=request.user)
    return render(request, 'modifier_profil_chef.html', {'form': form})


# --- ATTESTATIONS ---

@login_required
def voir_attestation(request, sinistre_id):
    sinistre = get_object_or_404(Sinistre, id=sinistre_id, attestation_generee=True)
    is_owner = (getattr(sinistre, 'assure', None) == request.user or getattr(sinistre, 'assure_id', None) == request.user.id)
    
    if is_owner or hasattr(request.user, 'agent') or hasattr(request.user, 'chef'):
        return render(request, 'attestation.html', {'sinistre': sinistre})
        
    return redirect('accueil_assure')


@login_required
def telecharger_attestation(request, sinistre_id):
    sinistre = get_object_or_404(Sinistre, id=sinistre_id, attestation_generee=True)
    is_owner = (getattr(sinistre, 'assure', None) == request.user or getattr(sinistre, 'assure_id', None) == request.user.id)
    
    if not (is_owner or hasattr(request.user, 'agent') or hasattr(request.user, 'chef')):
        return redirect('accueil_assure')

    return render(request, 'attestation.html', {'sinistre': sinistre, 'download_pdf': True})


# --- ESPACE ADMINISTRATEUR ---

@login_required
@user_passes_test(lambda u: u.is_staff)
def accueil_admin(request):
    sinistres = Sinistre.objects.all()
    debut_mois = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    context = {
        'nb_sinistres_total': sinistres.count(),
        'nb_sinistres_en_cours': sinistres.exclude(statut__in=['CLOTURE', 'SANS_SUITE']).count(),
        'nb_sinistres_clotures': sinistres.filter(statut='CLOTURE').count(),
        'nb_sinistres_mois': sinistres.filter(date_declaration__gte=debut_mois).count(),
        'nb_agences': Agence.objects.count(),
        'nb_agents': Agent.objects.count(),
        'nb_chefs': ChefDepartement.objects.count(),
        'nb_assures': Assure.objects.count(),
        'derniers_sinistres': sinistres.order_by('-date_declaration')[:8],
    }
    return render(request, 'accueil_admin.html', context)


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
            user.set_password('0000')
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
@user_passes_test(lambda u: u.is_staff)
def liste_agents(request):
    agents = Agent.objects.select_related('user', 'agence').order_by('user__last_name')
    return render(request, 'liste_agents.html', {'agents': agents})


@login_required
@user_passes_test(lambda u: u.is_staff)
def modifier_agent_admin(request, agent_id):
    agent = get_object_or_404(Agent, id=agent_id)
    if request.method == 'POST':
        user_form = ModifierProfilForm(request.POST, instance=agent.user)
        agent_form = ModifierAgentAdminForm(request.POST, instance=agent)
        if user_form.is_valid() and agent_form.is_valid():
            user_form.save()
            agent_form.save()
            messages.success(request, "Agent mis à jour.")
            return redirect('liste_agents')
    else:
        user_form = ModifierProfilForm(instance=agent.user)
        agent_form = ModifierAgentAdminForm(instance=agent)
    return render(request, 'modifier_agent_admin.html', {
        'user_form': user_form, 'agent_form': agent_form, 'agent': agent,
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def toggle_agent_actif(request, agent_id):
    agent = get_object_or_404(Agent, id=agent_id)
    agent.user.is_active = not agent.user.is_active
    agent.user.save()
    messages.success(request, f"Compte {'réactivé' if agent.user.is_active else 'désactivé'}.")
    return redirect('liste_agents')


@login_required
@user_passes_test(lambda u: u.is_staff)
def reinitialiser_mdp_agent(request, agent_id):
    agent = get_object_or_404(Agent, id=agent_id)
    agent.user.set_password('0000')
    agent.user.save()
    agent.doit_changer_mot_de_passe = True
    agent.save()
    messages.success(request, f"Mot de passe réinitialisé à 0000 pour {agent.user.get_full_name() or agent.user.username}.")
    return redirect('liste_agents')


@login_required
@user_passes_test(lambda u: u.is_staff)
def supprimer_agent(request, agent_id):
    agent = get_object_or_404(Agent, id=agent_id)
    if request.method == 'POST':
        agent.user.delete()
        messages.success(request, "Agent supprimé.")
        return redirect('liste_agents')
    return render(request, 'confirmer_suppression.html', {
        'objet_nom': agent.user.get_full_name() or agent.user.username,
        'type_objet': 'agent',
        'annuler_url': 'liste_agents',
        'confirmer_url': 'supprimer_agent',
        'objet_id': agent.id,
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def creer_chef(request):
    if request.method == 'POST':
        form = ChefCreationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            username = f"{data['prenom']}.{data['nom']}".lower().replace(' ', '')

            user = User.objects.create_user(
                username=username,
                email=data['email'],
                first_name=data['prenom'],
                last_name=data['nom'],
            )
            user.set_password('0000')
            user.save()

            ChefDepartement.objects.create(
                user=user,
                agence=data['agence'],
                matricule=data['matricule'],
                telephone=data['telephone'],
                doit_changer_mot_de_passe=True,
            )
            messages.success(request, f"Chef créé. Identifiant : {username} — Mot de passe temporaire : 0000")
            return redirect('creer_chef')
    else:
        form = ChefCreationForm()

    return render(request, 'creer_chef.html', {'form': form})


@login_required
@user_passes_test(lambda u: u.is_staff)
def liste_chefs(request):
    chefs = ChefDepartement.objects.select_related('user', 'agence').order_by('user__last_name')
    return render(request, 'liste_chefs.html', {'chefs': chefs})


@login_required
@user_passes_test(lambda u: u.is_staff)
def modifier_chef_admin(request, chef_id):
    chef = get_object_or_404(ChefDepartement, id=chef_id)
    if request.method == 'POST':
        user_form = ModifierProfilForm(request.POST, instance=chef.user)
        chef_form = ModifierChefAdminForm(request.POST, instance=chef)
        if user_form.is_valid() and chef_form.is_valid():
            user_form.save()
            chef_form.save()
            messages.success(request, "Chef mis à jour.")
            return redirect('liste_chefs')
    else:
        user_form = ModifierProfilForm(instance=chef.user)
        chef_form = ModifierChefAdminForm(instance=chef)
    return render(request, 'modifier_chef_admin.html', {
        'user_form': user_form, 'chef_form': chef_form, 'chef': chef,
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def toggle_chef_actif(request, chef_id):
    chef = get_object_or_404(ChefDepartement, id=chef_id)
    chef.user.is_active = not chef.user.is_active
    chef.user.save()
    messages.success(request, f"Compte {'réactivé' if chef.user.is_active else 'désactivé'}.")
    return redirect('liste_chefs')


@login_required
@user_passes_test(lambda u: u.is_staff)
def reinitialiser_mdp_chef(request, chef_id):
    chef = get_object_or_404(ChefDepartement, id=chef_id)
    chef.user.set_password('0000')
    chef.user.save()
    chef.doit_changer_mot_de_passe = True
    chef.save()
    messages.success(request, f"Mot de passe réinitialisé à 0000 pour {chef.user.get_full_name() or chef.user.username}.")
    return redirect('liste_chefs')


@login_required
@user_passes_test(lambda u: u.is_staff)
def supprimer_chef(request, chef_id):
    chef = get_object_or_404(ChefDepartement, id=chef_id)
    if request.method == 'POST':
        chef.user.delete()
        messages.success(request, "Chef supprimé.")
        return redirect('liste_chefs')
    return render(request, 'confirmer_suppression.html', {
        'objet_nom': chef.user.get_full_name() or chef.user.username,
        'type_objet': 'chef',
        'annuler_url': 'liste_chefs',
        'confirmer_url': 'supprimer_chef',
        'objet_id': chef.id,
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def liste_assures(request):
    assures = Assure.objects.select_related('user', 'agence').order_by('user__last_name')
    return render(request, 'liste_assures.html', {'assures': assures})


@login_required
@user_passes_test(lambda u: u.is_staff)
def toggle_assure_actif(request, assure_id):
    assure = get_object_or_404(Assure, id=assure_id)
    assure.user.is_active = not assure.user.is_active
    assure.user.save()
    messages.success(request, f"Compte {'réactivé' if assure.user.is_active else 'désactivé'}.")
    return redirect('liste_assures')


@login_required
@user_passes_test(lambda u: u.is_staff)
def supervision_sinistres(request):
    sinistres = Sinistre.objects.select_related('assure', 'vehicule', 'region').order_by('-date_declaration')

    statut = request.GET.get('statut', '')
    nature = request.GET.get('nature', '')
    recherche = request.GET.get('q', '').strip()

    if statut:
        sinistres = sinistres.filter(statut=statut)
    if nature:
        sinistres = sinistres.filter(nature=nature)
    if recherche:
        sinistres = sinistres.filter(
            Q(numero_sinistre__icontains=recherche) | Q(n_police__icontains=recherche)
        )

    context = {
        'sinistres': sinistres,
        'statut_choices': Sinistre.STATUS_CHOICES,
        'nature_choices': Sinistre.NATURE_CHOICES,
        'statut_selectionne': statut,
        'nature_selectionnee': nature,
        'recherche': recherche,
    }
    return render(request, 'supervision_sinistres.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def profil_admin(request):
    return render(request, 'profil_admin.html')


@login_required
@user_passes_test(lambda u: u.is_staff)
def modifier_profil_admin(request):
    if request.method == 'POST':
        form = ModifierProfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Vos informations ont été mises à jour.")
            return redirect('profil_admin')
    else:
        form = ModifierProfilForm(instance=request.user)
    return render(request, 'modifier_profil_admin.html', {'form': form})


@login_required
@user_passes_test(lambda u: u.is_staff)
def importer_donnees_admin(request):
    if request.method == 'POST':
        form = ImportExcelForm(request.POST, request.FILES)
        if form.is_valid():
            fichier = request.FILES['fichier']
            try:
                df = pd.read_excel(fichier)
                df.columns = [str(c).strip() for c in df.columns]
                
                def get_val(row, possible_keys):
                    for k in possible_keys:
                        for col in row.index:
                            if str(col).strip().lower().replace(' ', '_') == str(k).strip().lower().replace(' ', '_'):
                                val = row[col]
                                if pd.notna(val):
                                    return val
                    return None

                for index, row in df.iterrows():
                    type_contrat = str(get_val(row, ['TYPE_CONTRAT', 'TYPE CONTRAT', 'CONTRAT']) or '').strip()
                    if type_contrat.lower() != 'automobile':
                        continue  
                        
                    email_excel = get_val(row, ['EMAIL', 'COURRIEL', 'MAIL'])
                    if not email_excel:
                        continue
                    
                    if request.user.is_authenticated and email_excel == request.user.email:
                        continue
                    
                    if User.objects.filter(email=email_excel, is_staff=True).exists():
                        continue

                    numero_police = get_val(row, ['NUMERO_POLICE', 'NUMERO POLICE', 'NUMERO_CONTRAT', 'NUMERO CONTRAT'])
                    prenom = get_val(row, ['PRENOM', 'PRENOMS'])
                    nom = get_val(row, ['NOM'])
                    telephone = get_val(row, ['TELEPHONE', 'TEL'])
                    numero_quittance = get_val(row, ['NUMERO_QUITTANCE', 'NUMERO QUITTANCE', 'QUITTANCE'])
                    
                    if not numero_police or not numero_quittance:
                        continue

                    marque = get_val(row, ['MARQUE', 'MARQUE_VEHICULE']) or ''
                    modele = get_val(row, ['MODELE', 'MODELE_VEHICULE']) or None
                    immatriculation = get_val(row, ['IMMATRICULATION', 'IMMAT'])

                    user, user_created = User.objects.get_or_create(
                        email=email_excel,
                        defaults={
                            'username': email_excel,
                            'first_name': prenom or '',
                            'last_name': nom or '',
                            'is_active': False,
                        }
                    )
                    
                    if user.username == 'admin_fidelia' or user.is_staff:
                        continue

                    if prenom:
                        user.first_name = prenom
                    if nom:
                        user.last_name = nom
                    if user_created:
                        user.is_active = False  
                    user.save()

                    assure, created = Assure.objects.get_or_create(
                        numero_police=numero_police,
                        defaults={
                            'user': user,
                            'telephone': telephone,
                            'compte_active': False,
                        }
                    )

                    if not created:
                        assure.user = user
                        if telephone:
                            assure.telephone = telephone
                        assure.save()

                    date_debut = get_val(row, ['DATE_DEBUT', 'DATE DEBUT', 'DATE_EFFET', 'DATE EFFET'])
                    date_fin = get_val(row, ['DATE_FIN', 'DATE FIN', 'DATE_ECHEANCE', 'DATE ECHEANCE'])
                    prime = get_val(row, ['PRIME_NETTE', 'PRIME NETTE', 'PRIME'])

                    quittance, _ = Quittance.objects.update_or_create(
                        numero_quittance=numero_quittance,
                        defaults={
                            'contrat': assure,
                            'type_contrat': type_contrat,
                            'date_debut': date_debut,
                            'date_fin': date_fin,
                            'prime': prime
                        }
                    )

                    if immatriculation and marque:
                        Vehicule.objects.update_or_create(
                            immatriculation=immatriculation,
                            defaults={
                                'marque': marque,
                                'modele': modele,
                                'proprietaire': user,
                                'quittance': quittance,
                            }
                        )
                
                messages.success(request, "Importation des contrats et de leurs quittances réussie avec succès !")
                return redirect('accueil_admin')
                
            except Exception as e:
                messages.error(request, f"Erreur lors de l'importation : {e}")
    else:
        form = ImportExcelForm()
    
    return render(request, 'importer_donnees.html', {'form': form})


@login_required
@user_passes_test(lambda u: u.is_staff)
def liste_contrats_admin(request):
    quittances = Quittance.objects.select_related('contrat', 'contrat__user').order_by('contrat__user__last_name', 'contrat__user__first_name')
    query_police = request.GET.get('police', '').strip()
    query_nom = request.GET.get('nom', '').strip()
    query_type = request.GET.get('type_contrat', '').strip()

    if query_police:
        quittances = quittances.filter(contrat__numero_police__icontains=query_police)
    
    if query_nom:
        quittances = quittances.filter(
            Q(contrat__user__last_name__icontains=query_nom) | 
            Q(contrat__user__first_name__icontains=query_nom)
        )
        
    if query_type:
        quittances = quittances.filter(type_contrat__icontains=query_type)

    return render(request, 'liste_contrats.html', {
        'quittances': quittances,
        'query_police': query_police,
        'query_nom': query_nom,
        'query_type': query_type,
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def modifier_contrat_admin(request, assure_id):
    assure = get_object_or_404(Assure, id=assure_id)
    if request.method == 'POST':
        form = AssureAdminForm(request.POST, instance=assure)
        if form.is_valid():
            form.save()
            messages.success(request, "Le contrat a été mis à jour avec succès.")
            return redirect('liste_contrats')
    else:
        form = AssureAdminForm(instance=assure)

    return render(request, 'modifier_contrat.html', {'form': form, 'assure': assure})


@login_required
@user_passes_test(lambda u: u.is_staff)
def supprimer_contrat_admin(request, assure_id):
    assure = get_object_or_404(Assure, id=assure_id)
    if request.method == 'POST':
        nom_complet = assure.user.get_full_name() or assure.user.username
        assure.user.delete()
        messages.success(request, f"Le contrat et le compte de {nom_complet} ont été supprimés.")
        return redirect('liste_contrats')

    return render(request, 'confirmer_suppression.html', {
        'objet_nom': f"Contrat {assure.numero_police} ({assure.user.get_full_name()})",
        'type_objet': 'contrat',
        'annuler_url': reverse('liste_contrats'),
        'confirmer_url': 'supprimer_contrat_admin',
        'objet_id': assure.id,
    })


@login_required
def demander_revision_prix(request, sinistre_id):
    chef = getattr(request.user, 'chef', None)
    if not chef:
        return redirect('accueil_assure')

    # Récupération du sinistre en attente de validation ou en cours
    sinistre = get_object_or_404(Sinistre, id=sinistre_id, statut__in=['ATTENTE_VALIDATION', 'EN_COURS'])

    if request.method == 'POST':
        commentaires = request.POST.get('commentaires', '').strip()

        # 1. Passer le dossier au statut 'A_CORRIGER'
        sinistre.statut = 'A_CORRIGER'
        sinistre.indemnisation_validee = False
        sinistre.save()

        # 2. Historiser le motif explicatif
        HistoriqueSinistre.objects.create(
            sinistre=sinistre,
            statut='A_CORRIGER',
            commentaires=commentaires or "Demande de révision envoyée à l'agent.",
            auteur=request.user,
        )

        # 3. Notification de succès pour le chef
        messages.success(
            request, 
            f"✅ Le dossier {sinistre.numero_sinistre} a bien été renvoyé dans la file d'attente de l'agent."
        )

        # Redirection vers la liste des dossiers à valider du chef
        return redirect('dossiers_a_valider') 

    return render(request, 'demander_revision.html', {'sinistre': sinistre})