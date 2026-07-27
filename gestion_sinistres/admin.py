from django.contrib import admin
from .models import Sinistre, Region, Commune, Ville, Vehicule, PieceJointe, Assure, Agence, Agent, ChefDepartement, Quittance

# Personnalisation de l'affichage dans l'admin
@admin.register(Sinistre)
class SinistreAdmin(admin.ModelAdmin):
    list_display = ('numero_sinistre', 'assure', 'statut', 'date_declaration', 'nature')
    list_filter = ('statut', 'nature', 'date_declaration')
    search_fields = ('numero_sinistre', 'assure__username')

@admin.register(Vehicule)
class VehiculeAdmin(admin.ModelAdmin):
    list_display = ('id', 'immatriculation', 'marque', 'modele', 'annee', 'proprietaire')
    search_fields = ('immatriculation', 'marque', 'modele', 'proprietaire__username')
    

@admin.register(PieceJointe)
class PieceJointeAdmin(admin.ModelAdmin):
    list_display = ('sinistre', 'date_ajout')

@admin.register(Quittance)
class QuittanceAdmin(admin.ModelAdmin):
    list_display = ('numero_quittance', 'contrat', 'date_debut', 'date_fin', 'prime')
    list_filter = ('date_debut', 'date_fin')
    search_fields = ('numero_quittance', 'contrat__numero_police')

    
# Enregistrement simple pour les tables de référence
admin.site.register(Region)
admin.site.register(Commune)
admin.site.register(Ville)
admin.site.register(Assure)
admin.site.register(Agence)
admin.site.register(Agent)
admin.site.register(ChefDepartement)