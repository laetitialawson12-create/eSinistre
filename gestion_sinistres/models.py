from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime
from django.contrib.auth.models import User

# Classe région
class Region(models.Model):
    nom = models.CharField(max_length=100)
    def __str__(self): return self.nom

# Classe ville
class Ville(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    nom = models.CharField(max_length=100)
    def __str__(self): return self.nom

# Classe préfecture
class Prefecture(models.Model):
    ville = models.ForeignKey(Ville, on_delete=models.CASCADE)
    nom = models.CharField(max_length=100)
    def __str__(self): return self.nom

# Véhicule
class Vehicule(models.Model):
    immatriculation = models.CharField(max_length=20, unique=True)
    marque = models.CharField(max_length=50)
    modele = models.CharField(max_length=50)
    annee = models.IntegerField()
    proprietaire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicules')

    def __str__(self):
        return f"{self.immatriculation} - {self.marque} {self.modele}"
    
# Classe sinistre
class Sinistre(models.Model):
    NATURE_CHOICES = [('C', 'Corporel'), ('M', 'Matériel'), ('X', 'Mixte')]

    # STATUTS
    STATUS_CHOICES = [
        ('SOUMIS', 'Soumis'),
        ('ATTENTE_COMPLEMENTS', 'En attente de compléments'),
        ('ATTENTE_VALIDATION', 'En attente de validation'),
        ('A_CORRIGER', 'A corriger'),
        ('EN_COURS', 'En cours'),
        ('CLOTURE', 'Clôturé'),
        ('SANS_SUITE', 'Sans suite'),
        ('REOUVERT', 'Réouvert'),
    ]

    n_police = models.CharField(max_length=50)
    nom_conducteur = models.CharField(max_length=100) 
    immatriculation = models.CharField(max_length=20)

    # Identifiants
    numero_sinistre = models.CharField(max_length=20, unique=True)
    statut = models.CharField(max_length=30, choices=STATUS_CHOICES, default='SOUMIS')
    agent_traitant = models.CharField(max_length=100, blank=True, null=True)

    montant_estime = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Informations de base 
    date_survenance = models.DateTimeField()
    date_declaration = models.DateTimeField(auto_now_add=True)
    heure_approximative = models.TimeField()
    circonstances = models.TextField()
    vehicule = models.ForeignKey(Vehicule, on_delete=models.CASCADE)

    # Localisation
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True)
    ville = models.ForeignKey(Ville, on_delete=models.SET_NULL, null=True)
    prefecture = models.ForeignKey(Prefecture, on_delete=models.SET_NULL, null=True)
    quartier = models.CharField(max_length=150)

    # Détails du sinistre
    nature = models.CharField(max_length=1, choices=NATURE_CHOICES)
    precision = models.TextField(help_text="Circonstances exactes")

    # Informations pour la génération du numéro
    numero_point_vente = models.CharField(max_length=10, default="001")
    assure = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sinistres')

    # Pièces jointes
    lettre_derogation = models.FileField(upload_to='sinistres/derogations/', blank=True, null=True)

    def save(self, *args, **kwargs):
        # Génération automatique du numéro de sinistre à la création
        if not self.numero_sinistre:
            annee = datetime.now().strftime('%Y')
            count = Sinistre.objects.filter(
                numero_sinistre__startswith = f"{annee}{self.numero_point_vente}"
            ).count() + 1
            ordre = str(count).zfill(6)
            self.numero_sinistre = f"{annee}{self.numero_point_vente}{self.nature}{ordre}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Sinistre {self.numero_sinistre} - {self.nature}"


class PieceJointe(models.Model):
    sinistre = models.ForeignKey(Sinistre, on_delete=models.CASCADE, related_name='pieces')
    fichier = models.FileField(upload_to='sinistres/documents/')
    date_ajout = models.DateTimeField(auto_now_add=True)


class HistoriqueSinistre(models.Model):
    sinistre = models.ForeignKey(Sinistre, on_delete=models.CASCADE, related_name='historique')
    statut = models.CharField(max_length=50)
    date_changement = models.DateTimeField(auto_now_add=True)
    commentaires = models.TextField(blank=True)
    auteur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)


class EtapeSinistre(models.Model):
    sinistre = models.ForeignKey(Sinistre, on_delete=models.CASCADE, related_name='etapes')
    titre = models.CharField(max_length=200)
    date_etape = models.DateTimeField(auto_now_add=True)
    description = models.TextField()


class Message(models.Model):
    sinistre = models.ForeignKey(Sinistre, on_delete=models.CASCADE, related_name='messages')
    auteur = models.ForeignKey(User, on_delete=models.CASCADE)
    contenu = models.TextField()
    date_envoi = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message de {self.auteur.username} le {self.date_envoi.strftime('%d/%m')}"