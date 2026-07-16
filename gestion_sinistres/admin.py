from django.contrib import admin
from .models import Sinistre, Region, Ville, Prefecture, Vehicule, PieceJointe

admin.site.register(Region)
admin.site.register(Ville)
admin.site.register(Prefecture)
admin.site.register(Sinistre)
admin.site.register(Vehicule)
admin.site.register(PieceJointe)