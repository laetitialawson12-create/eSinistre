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
    if not profil or not hasattr(profil, 'bloque_jusqu_a'):
        return False
    return bool(profil.bloque_jusqu_a and profil.bloque_jusqu_a > timezone.now())

def enregistrer_echec(identifiant):
    profil = get_profil_par_identifiant(identifiant)
    if not profil or not hasattr(profil, 'tentatives_echouees'):
        return
    
    profil.tentatives_echouees += 1
    if profil.tentatives_echouees >= SEUIL_TENTATIVES:
        if hasattr(profil, 'bloque_jusqu_a'):
            profil.bloque_jusqu_a = timezone.now() + DUREE_BLOCAGE
            profil.save(update_fields=['tentatives_echouees', 'bloque_jusqu_a'])
            return
            
    profil.save(update_fields=['tentatives_echouees'])

def reinitialiser_tentatives(profil):
    if not profil:
        return
    
    fields_to_update = []
    if hasattr(profil, 'tentatives_echouees'):
        profil.tentatives_echouees = 0
        fields_to_update.append('tentatives_echouees')
        
    if hasattr(profil, 'bloque_jusqu_a'):
        profil.bloque_jusqu_a = None
        fields_to_update.append('bloque_jusqu_a')
        
    if fields_to_update:
        profil.save(update_fields=fields_to_update)