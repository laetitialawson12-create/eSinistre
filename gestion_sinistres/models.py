from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import datetime

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
    modele = models.CharField(max_length=50, null=True, blank=True)
    annee = models.IntegerField(null=True, blank=True)
    proprietaire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicules', null=True, blank=True)
    quittance = models.ForeignKey('Quittance', on_delete=models.CASCADE, related_name='vehicules', null=True, blank=True)

    def __str__(self):
        return f"{self.immatriculation} - {self.marque} {self.modele or 'Modèle non spécifié'}"
    
    
class Quittance(models.Model):
    contrat = models.ForeignKey('Assure', on_delete=models.CASCADE, related_name='quittances')
    numero_quittance = models.CharField(max_length=50, unique=True)
    type_contrat = models.CharField(max_length=100, blank=True, null=True)
    date_debut = models.DateField()
    date_fin = models.DateField()
    prime = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"Quittance N° {self.numero_quittance}"
    
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
    prix_retenu = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Indemnisation (chèque remis au bénéficiaire, saisi après clôture)
    beneficiaire_nom = models.CharField(max_length=100, blank=True, null=True)
    beneficiaire_prenoms = models.CharField(max_length=100, blank=True, null=True)
    beneficiaire_telephone = models.CharField(max_length=20, blank=True, null=True)
    numero_cheque = models.CharField(max_length=50, blank=True, null=True)
    banque_cheque = models.CharField(max_length=100, blank=True, null=True)
    montant_cheque = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    date_emission_cheque = models.DateField(null=True, blank=True)
    attestation_generee = models.BooleanField(default=False)
    date_attestation = models.DateTimeField(null=True, blank=True)
    motif_sans_suite = models.TextField(blank=True, null=True)
    indemnisation_validee = models.BooleanField(default=False)
    

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

    quittance = models.ForeignKey(Quittance, on_delete=models.SET_NULL, null=True, blank=True)
    
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
    

class Agence(models.Model):
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)  # ex: "001"

    def __str__(self):
        return f"{self.nom} ({self.code})"
    

class Assure(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='assure')
    numero_police = models.CharField(max_length=50, unique=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    agence = models.ForeignKey(Agence, on_delete=models.SET_NULL, null=True, blank=True)
    compte_active = models.BooleanField(default=False)
    politique_confidentialite_acceptee = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.numero_police}"


class Agent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='agent')
    agence = models.ForeignKey(Agence, on_delete=models.SET_NULL, null=True)
    matricule = models.CharField(max_length=20, unique=True)
    telephone = models.CharField(max_length=20, blank=True)
    compte_active = models.BooleanField(default=False)
    doit_changer_mot_de_passe = models.BooleanField(default=True)   # ← nouveau

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.agence}"
    

class ChefDepartement(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chef')
    agence = models.ForeignKey(Agence, on_delete=models.SET_NULL, null=True)
    matricule = models.CharField(max_length=20, unique=True)
    telephone = models.CharField(max_length=20, blank=True)
    compte_active = models.BooleanField(default=False)
    doit_changer_mot_de_passe = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - Chef"