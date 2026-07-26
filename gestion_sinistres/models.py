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
    
    # Champs financiers
    prime = models.DecimalField(max_digits=12, decimal_places=2)  # Représente la prime nette
    prix_retenu = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    prix_valide = models.BooleanField(default=False)
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(prix_retenu__lte=models.F('prime')),
                name='check_prix_retenu_lte_prime'
            ),
            models.CheckConstraint(
                condition=models.Q(date_debut__lte=models.F('date_fin')),
                name='check_quittance_date_debut_lte_date_fin'
            ),
        ]

    def clean(self):
        super().clean()

        # Validation logique : prix_retenu <= prime
        if self.prix_retenu is not None and self.prime is not None:
            if self.prix_retenu > self.prime:
                raise ValidationError({
                    'prix_retenu': "Le prix retenu ne peut pas être supérieur à la prime."
                })

        # Validation logique : date_debut <= date_fin
        if self.date_debut and self.date_fin and self.date_debut > self.date_fin:
            raise ValidationError({
                'date_fin': "La date de fin doit être postérieure ou égale à la date de début."
            })

    def save(self, *args, **kwargs):
        # Force l'exécution de clean() avant tout enregistrement
        self.full_clean()
        super().save(*args, **kwargs)

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
        ('CHEQUE_EMIS', 'Chèque émis'),
        ('CLOTURE', 'Clôturé'),
        ('SANS_SUITE', 'Sans suite'),
        ('REOUVERT', 'Réouvert'),
    ]

    nom_conducteur = models.CharField(max_length=100) 
    immatriculation = models.CharField(max_length=50, blank=True, null=True, verbose_name="Immatriculation")

    # Identifiants
    numero_sinistre = models.CharField(max_length=20, unique=True)
    statut = models.CharField(max_length=30, choices=STATUS_CHOICES, default='SOUMIS')
    agent_traitant = models.CharField(max_length=100, blank=True, null=True)

    montant_estime = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    prix_retenu = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

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

    # Informations pour la génération du numéro
    numero_point_vente = models.CharField(max_length=10, default="001")
    assure = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sinistres')

    quittance = models.ForeignKey(Quittance, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Pièces jointes
    lettre_derogation = models.FileField(upload_to='sinistres/derogations/', blank=True, null=True)

    @property
    def total_paye(self):
        """Calcule la somme totale des paiements/chèques émis pour ce sinistre"""
        return sum(p.montant for p in self.paiements.all())

    @property
    def reste_a_payer(self):
        """Calcule le montant restant à verser par rapport au prix retenu"""
        if not self.prix_retenu:
            return 0
        return self.prix_retenu - self.total_paye

    def clean(self):
        super().clean()

        if self.prix_retenu is not None and self.prix_retenu < 0:
            raise ValidationError({
                'prix_retenu': f"Le prix retenu ({self.prix_retenu} FCFA) ne peut pas être négatif."
            })

    def save(self, *args, **kwargs):
        # 1. Génération automatique du numéro de sinistre à la création
        if not self.numero_sinistre:
            annee = timezone.now().strftime('%Y')
            count = Sinistre.objects.filter(
                numero_sinistre__startswith=f"{annee}{self.numero_point_vente}"
            ).count() + 1
            ordre = str(count).zfill(6)
            self.numero_sinistre = f"{annee}{self.numero_point_vente}{self.nature}{ordre}"

        # 2. Exécute la méthode clean() pour forcer la validation avant sauvegarde
        self.full_clean()

        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Sinistre {self.numero_sinistre} - {self.nature}"


class Paiement(models.Model):
    sinistre = models.ForeignKey(Sinistre, on_delete=models.CASCADE, related_name='paiements')
    numero_cheque = models.CharField(max_length=100)
    banque_cheque = models.CharField(max_length=100)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    beneficiaire_nom = models.CharField(max_length=100)
    beneficiaire_prenoms = models.CharField(max_length=150)
    beneficiaire_telephone = models.CharField(max_length=20)
    date_emission = models.DateField()
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chèque n°{self.numero_cheque} - {self.montant} FCFA"
        
    
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


# models.py
from django.db import models

class Cheque(models.Model):
    STATUT_CHEQUE = [
        ('EN_PREPARATION', 'En cours de préparation'),
        ('DISPONIBLE', 'Prêt pour retrait'),
        ('RETIRE', 'Retiré par l\'assuré'),
        ('ANNULE', 'Annulé'),
    ]

    sinistre = models.OneToOneField(
        'Sinistre', 
        on_delete=models.CASCADE, 
        related_name='cheque',
        verbose_name="Sinistre associé"
    )
    numero_cheque = models.CharField(max_length=50, unique=True, verbose_name="Numéro du chèque")
    banque_emettrice = models.CharField(max_length=100, verbose_name="Banque émettrice")
    montant = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Montant (FCFA)")
    beneficiaire = models.CharField(max_length=200, verbose_name="Nom du bénéficiaire")
    
    statut = models.CharField(max_length=20, choices=STATUT_CHEQUE, default='EN_PREPARATION')
    
    date_emission = models.DateField(auto_now_add=True, verbose_name="Date d'émission")
    date_disponibilite = models.DateField(null=True, blank=True, verbose_name="Date de disponibilité")
    date_retrait = models.DateField(null=True, blank=True, verbose_name="Date de retrait")
    
    agent_emetteur = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="Agent ayant émis le chèque"
    )

    def __str__(self):
        return f"Chèque N° {self.numero_cheque} - {self.montant} FCFA ({self.get_statut_display()})"