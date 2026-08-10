from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .forms import EsinistreAuthentificationForm
from . import views

urlpatterns = [
    # ==========================================
    # 1. AUTHENTIFICATION & ACTIVATION
    # ==========================================
    path('login/', LoginView.as_view(template_name='login.html', authentication_form=EsinistreAuthentificationForm), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('redirection/', views.redirection_login, name='redirection_login'),
    path('activer-compte/', views.activation_etape1, name='activation_etape1'),
    path('activer-compte/mot-de-passe/', views.activation_etape2, name='activation_etape2'),
    path('politique-confidentialite/', views.politique_confidentialite, name='politique_confidentialite'),

    # ==========================================
    # 2. ESPACE ASSURÉ
    # ==========================================
    path('accueil/', views.accueil_assure, name='accueil_assure'),
    path('mes-contrats/', views.mes_contrats, name='mes_contrats'),
    path('declarer/', views.declarer_sinistre, name='declarer_sinistre'),
    path('declarer/annuler/', views.annuler_declaration, name='annuler_declaration'),
    path('confirmation/', views.confirmer_sinistre, name='confirmer_sinistre'),
    path('finaliser/', views.finaliser_envoi, name='finaliser_envoi'),
    path('suivi/', views.suivi_sinistres, name='suivi_sinistres'),
    path('documents/', views.documents_assure, name='documents_assure'),
    path('dossier/<int:sinistre_id>/', views.detail_sinistre, name='detail_sinistre'),
    path('sinistres/<int:sinistre_id>/complements/', views.fournir_complements, name='fournir_complements'),
    path('profil/', views.profil_assure, name='profil_assure'),
    path('profil/modifier/', views.modifier_profil, name='modifier_profil'),
    path('mes-contrats/<int:quittance_id>/', views.detail_contrat_assure, name='detail_contrat_assure'),
    path('agent/profil/changer-mot-de-passe_en_cours_assure/', views.changer_mot_de_passe_en_cours_assure, name='changer_mot_de_passe_en_cours_assure'),

    # ==========================================
    # 3. ESPACE AGENT
    # ==========================================
    path('agent/accueil/', views.accueil_agent, name='accueil_agent'),
    path('agent/profil/', views.profil_agent, name='profil_agent'),
    path('agent/profil/modifier/', views.modifier_profil_agent, name='modifier_profil_agent'),
    path('agent/changer-mot-de-passe/', views.changer_mot_de_passe_agent, name='changer_mot_de_passe_agent'),
    path('agent/a-valider/', views.dossiers_a_valider_agent, name='dossiers_a_valider_agent'),
    path('agent/en-cours/', views.dossiers_en_cours, name='dossiers_en_cours'),
    path('agent/a-corriger/', views.dossiers_a_corriger_agent, name='dossiers_a_corriger_agent'),
    path('agent/clotures/', views.dossiers_clotures, name='dossiers_clotures'),
    path('agent/sinistres/', views.tous_sinistres_agent, name='tous_sinistres_agent'),
    path('agent/dossier/<int:sinistre_id>/', views.detail_sinistre_agent, name='detail_sinistre_agent'),
    path('agent/dossier/<int:sinistre_id>/ajouter-numero-sinistre', views.ajouter_numero_sinistre, name='ajouter_numero_sinistre'),
    path('agent/dossier/<int:sinistre_id>/prendre/', views.prendre_en_charge, name='prendre_en_charge'),
    path('agent/dossier/<int:sinistre_id>/conforme/', views.marquer_conforme, name='marquer_conforme'),
    path('agent/dossier/<int:sinistre_id>/complements/', views.demander_complements, name='demander_complements'),
    path('agent/dossier/<int:sinistre_id>/indemnisation/', views.saisir_indemnisation, name='saisir_indemnisation'),
    path('agent/dossier/<int:sinistre_id>/prix-retenu/', views.saisir_prix_retenu, name='saisir_prix_retenu'),
    path('agent/dossier/<int:sinistre_id>/emettre-cheque/', views.emettre_cheque, name='emettre_cheque'),
    path('paiement/<int:paiement_id>/modifier-statut/', views.modifier_statut_cheque, name='modifier_statut_cheque'),
    path('paiement/<int:paiement_id>/retrait/', views.marquer_cheque_retire, name='marquer_cheque_retire'),
    path('agent/profil/changer-mot-de-passe_en_cours_agent/', views.changer_mot_de_passe_en_cours_agent, name='changer_mot_de_passe_en_cours_agent'),


    # ==========================================
    # 4. ESPACE CHEF DE DÉPARTEMENT
    # ==========================================
    path('chef/accueil/', views.accueil_chef, name='accueil_chef'),
    path('chef/profil/', views.profil_chef, name='profil_chef'),
    path('chef/profil/modifier/', views.modifier_profil_chef, name='modifier_profil_chef'),
    path('chef/changer-mot-de-passe/', views.changer_mot_de_passe_chef, name='changer_mot_de_passe_chef'),
    path('chef/a-valider/', views.dossiers_a_valider, name='dossiers_a_valider'),
    path('chef/en-cours/', views.dossiers_en_cours_chef, name='dossiers_en_cours_chef'),
    path('chef/a-corriger/', views.dossiers_a_corriger_chef, name='dossiers_a_corriger_chef'),
    path('chef/clotures/', views.dossiers_clotures_chef, name='dossiers_clotures_chef'),
    path('chef/dossier/<int:sinistre_id>/', views.detail_sinistre_chef, name='detail_sinistre_chef'),
    path('chef/dossier/<int:sinistre_id>/valider/', views.valider_declaration, name='valider_declaration'),
    path('chef/dossier/<int:sinistre_id>/renvoyer/', views.renvoyer_a_agent, name='renvoyer_a_agent'),
    path('chef/dossier/<int:sinistre_id>/valider-indemnisation/', views.valider_indemnisation, name='valider_indemnisation'),
    path('chef/dossier/<int:sinistre_id>/cloturer/', views.clore_sinistre, name='clore_sinistre'),
    path('chef/dossier/<int:sinistre_id>/sans-suite/', views.classer_sans_suite, name='classer_sans_suite'),
    path('chef/dossier/<int:sinistre_id>/reouvrir/', views.reouvrir_dossier, name='reouvrir_dossier'),
    path('chef/sinistre/<int:sinistre_id>/demander-revision/', views.demander_revision_prix, name='demander_revision_prix'),
    path('agent/profil/changer-mot-de-passe_en_cours_chef/', views.changer_mot_de_passe_en_cours_chef, name='changer_mot_de_passe_en_cours_chef'),

    # ==========================================
    # 5. ESPACE ADMINISTRATION
    # ==========================================
    path('admin/accueil/', views.accueil_admin, name='accueil_admin'),
    path('admin/profil/', views.profil_admin, name='profil_admin'),
    path('admin/profil/modifier/', views.modifier_profil_admin, name='modifier_profil_admin'),
    path('admin/importer-donnees/', views.importer_donnees_admin, name='importer_donnees'),
    path('admin/sinistres/', views.supervision_sinistres, name='supervision_sinistres'),
    path('admin/profil/changer-mot-de-passe_en_cours_admin/', views.changer_mot_de_passe_en_cours_admin, name='changer_mot_de_passe_en_cours_admin'),

    # Gestion des Agents par Admin
    path('admin/agents/', views.liste_agents, name='liste_agents'),
    path('admin/agents/creer/', views.creer_agent, name='creer_agent'),
    path('admin/agents/<int:agent_id>/modifier/', views.modifier_agent_admin, name='modifier_agent_admin'),
    path('admin/agents/<int:agent_id>/toggle/', views.toggle_agent_actif, name='toggle_agent_actif'),
    path('admin/agents/<int:agent_id>/supprimer/', views.supprimer_agent, name='supprimer_agent'),
    path('admin/agents/<int:agent_id>/reinitialiser-mdp/', views.reinitialiser_mdp_agent, name='reinitialiser_mdp_agent'),

    # Gestion des Chefs par Admin
    path('admin/chefs/', views.liste_chefs, name='liste_chefs'),
    path('admin/chefs/creer/', views.creer_chef, name='creer_chef'),
    path('admin/chefs/<int:chef_id>/modifier/', views.modifier_chef_admin, name='modifier_chef_admin'),
    path('admin/chefs/<int:chef_id>/toggle/', views.toggle_chef_actif, name='toggle_chef_actif'),
    path('admin/chefs/<int:chef_id>/supprimer/', views.supprimer_chef, name='supprimer_chef'),
    path('admin/chefs/<int:chef_id>/reinitialiser-mdp/', views.reinitialiser_mdp_chef, name='reinitialiser_mdp_chef'),

    # Gestion des Assurés et Contrats par Admin
    path('admin/assures/', views.liste_assures, name='liste_assures'),
    path('admin/assures/<int:assure_id>/toggle/', views.toggle_assure_actif, name='toggle_assure_actif'),
    path('admin/contrats/', views.liste_contrats_admin, name='liste_contrats'),
    path('admin/contrats/<int:assure_id>/modifier/', views.modifier_contrat_admin, name='modifier_contrat_admin'),
    path('admin/contrats/<int:assure_id>/supprimer/', views.supprimer_contrat_admin, name='supprimer_contrat_admin'),

    # Administration — localisation
    path('admin/localisation/', views.gestion_localisation, name='gestion_localisation'),
    path('admin/localisation/region/<int:region_id>/supprimer/', views.supprimer_region, name='supprimer_region'),
    path('admin/localisation/commune/<int:commune_id>/supprimer/', views.supprimer_Commune, name='supprimer_commune'),
    path('admin/localisation/ville/<int:ville_id>/supprimer/', views.supprimer_ville, name='supprimer_ville'),

    # Administration — export contrats
    path('admin/contrats/exporter/', views.exporter_contrats_admin, name='exporter_contrats'),

    # Création des agences
    path('admin/agences/', views.gestion_agences, name='gestion_agences'),

    # ==========================================
    # 6. ATTESTATIONS & DOCUMENTS
    # ==========================================
    path('attestation/<int:sinistre_id>/', views.voir_attestation, name='voir_attestation'),
    path('attestation/<int:sinistre_id>/telecharger/', views.telecharger_attestation, name='telecharger_attestation'),

    # Authentification - mot de passe oublié
    path('mot-de-passe-oublie/', views.mot_de_passe_oublie_etape1, name='mot_de_passe_oublie_etape1'),
    path('mot-de-passe-oublie/nouveau/', views.mot_de_passe_oublie_etape2, name='mot_de_passe_oublie_etape2'),

]