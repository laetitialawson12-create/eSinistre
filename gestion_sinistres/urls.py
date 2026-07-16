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
    path('profil/', views.profil_assure, name='profil_assure'),
]
