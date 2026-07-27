from django.utils import timezone
from datetime import timedelta
from .models import Assure, Agent, ChefDepartement

DUREE_BLOCAGE = timedelta(minutes=5)
SEUIL_TENTATIVES = 3

def get_profil_par_identifiant(identifiant):
    if not identifiant:
        return None

    assure = Assure.objects.filter(numero_police=identifiant).first()
    if assure:
        return assure

    agent = Agent.objects.filter(user__username=identifiant).first()
    if agent:
        return agent

    chef = ChefDepartement.objects.filter(user__username=identifiant).first()
    if chef:
        return chef

    return None 


def profil_est_bloque(profil):
    return bool(profil and profil.bloque__jusqu_a and profil.bloque__jusqu_a > timezone.now())


def enregistrer_echec(identifiant):
    profil = get_profil_par_identifiant(identifiant)
    if not profil:
        return
    profil.tentatives_echouees += 1
    if profil.tentatives_echouees >= SEUIL_TENTATIVES:
        profil.bloque_jusqu_a = timezone.now() + DUREE_BLOCAGE
    profil.save(update_fields=['tentaives_echouees', 'bloque__jusqu_a'])


def reinitialiser_tentatives(profil):
    if not profil:
        return
    profil.tentatives_echouees = 0
    profil.bloque__jusqu_a = None
    profil.save(update_fields=['tentatives_echouees', 'bloque__jusqu_a'])