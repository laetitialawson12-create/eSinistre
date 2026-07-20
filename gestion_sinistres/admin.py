from django.contrib import admin
from .models import Sinistre, Region, Ville, Prefecture, Vehicule, PieceJointe, Assure, Agence, Agent, ChefDepartement

# Personnalisation de l'affichage dans l'admin
@admin.register(Sinistre)
class SinistreAdmin(admin.ModelAdmin):
    list_display = ('numero_sinistre', 'assure', 'statut', 'date_declaration', 'nature')
    list_filter = ('statut', 'nature', 'date_declaration')
    search_fields = ('numero_sinistre', 'assure__username')

@admin.register(Vehicule)
class VehiculeAdmin(admin.ModelAdmin):
    list_display = ('immatriculation', 'marque', 'modele', 'proprietaire')
    search_fields = ('immatriculation', 'proprietaire__username')

@admin.register(PieceJointe)
class PieceJointeAdmin(admin.ModelAdmin):
    list_display = ('sinistre', 'date_ajout')

# Enregistrement simple pour les tables de référence
admin.site.register(Region)
admin.site.register(Ville)
admin.site.register(Prefecture)
admin.site.register(Assure)
admin.site.register(Agence)
admin.site.register(Agent)
admin.site.register(ChefDepartement)