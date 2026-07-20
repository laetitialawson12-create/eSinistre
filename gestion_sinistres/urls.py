from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

urlpatterns = [
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),


    path('accueil/', views.accueil_assure, name='accueil_assure'),
    path('declarer/', views.declarer_sinistre, name='declarer_sinistre'),
    path('confirmation/', views.confirmer_sinistre, name='confirmer_sinistre'),
    path('finaliser/', views.finaliser_envoi, name='finaliser_envoi'),
    path('suivi/', views.suivi_sinistres, name='suivi_sinistres'),
    path('documents/', views.documents_assure, name='documents_assure'),
    path('dossier/<int:sinistre_id>/', views.detail_sinistre, name='detail_sinistre'),
    path('profil/', views.profil_assure, name='profil_assure'),
    path('profil/modifier/', views.modifier_profil, name='modifier_profil'),
    path('declarer/annuler/', views.annuler_declaration, name='annuler_declaration'),
    path('activer-compte/', views.activation_etape1, name='activation_etape1'),
    path('activer-compte/mot-de-passe/', views.activation_etape2, name='activation_etape2'),
    path('politique-confidentialite/', views.politique_confidentialite, name='politique_confidentialite'),
    path('redirection/', views.redirection_login, name='redirection_login'),
    path('agent/accueil/', views.accueil_agent, name='accueil_agent'),
    path('agent/changer-mot-de-passe/', views.changer_mot_de_passe_agent, name='changer_mot_de_passe_agent'),
    path('admin-agents/creer/', views.creer_agent, name='creer_agent'),
    path('agent/a-instruire/', views.dossiers_a_instruire, name='dossiers_a_instruire'),
    path('agent/dossier/<int:sinistre_id>/prendre/', views.prendre_en_charge, name='prendre_en_charge'),
    path('agent/dossier/<int:sinistre_id>/', views.detail_sinistre_agent, name='detail_sinistre_agent'),
    path('agent/dossier/<int:sinistre_id>/conforme/', views.marquer_conforme, name='marquer_conforme'),
    path('agent/dossier/<int:sinistre_id>/complements/', views.demander_complements, name='demander_complements'),
    path('agent/dossier/<int:sinistre_id>/indemnisation/', views.saisir_indemnisation, name='saisir_indemnisation'),
    path('agent/en-cours/', views.dossiers_en_cours, name='dossiers_en_cours'),
    path('agent/clotures/', views.dossiers_clotures, name='dossiers_clotures'),
    path('agent/dossier/<int:sinistre_id>/prix-retenu/', views.saisir_prix_retenu, name='saisir_prix_retenu'),
    path('chef/accueil/', views.accueil_chef, name='accueil_chef'),
    path('chef/a-valider/', views.dossiers_a_valider, name='dossiers_a_valider'),
    path('chef/dossier/<int:sinistre_id>/', views.detail_sinistre_chef, name='detail_sinistre_chef'),
    path('chef/dossier/<int:sinistre_id>/valider/', views.valider_declaration, name='valider_declaration'),
    path('chef/dossier/<int:sinistre_id>/renvoyer/', views.renvoyer_a_agent, name='renvoyer_a_agent'),
    path('admin-chefs/creer/', views.creer_chef, name='creer_chef'),
    path('chef/changer-mot-de-passe/', views.changer_mot_de_passe_chef, name='changer_mot_de_passe_chef'),
]