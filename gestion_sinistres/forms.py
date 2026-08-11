from django import forms
from django.utils import timezone
from datetime import timedelta
from .models import Sinistre, Agent, Agence, ChefDepartement, Assure, Quittance, Vehicule, Cheque, Region, Ville, Commune, Paiement
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from .auth_utils import get_profil_par_identifiant, profil_est_bloque, enregistrer_echec, reinitialiser_tentatives


class StylePasswordChangeForm(PasswordChangeForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields['old_password'].widget.attrs.update({'class': 'form-control'})
        self.fields['new_password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['new_password2'].widget.attrs.update({'class': 'form-control'})
        
        
# CALCUL DES JOURS
def jours_ouvres_entre(date_debut, date_fin):
    # jours = Jours ouvrés
    jours = 0
    date_courante = date_debut
    while date_courante < date_fin:
        date_courante += timedelta(days=1)
        # Vérifie si le jour de la semaine (weekday) est inférieur à 5 (Lundi=0; Vendredi=4)
        if date_courante.weekday() < 5:
            jours += 1
    return jours


# GESTION DES FICHIERS MULTIPLES
class MultipleFileInput(forms.ClearableFileInput):
    # Autorise l'attribut HTML 'multiple' pour sélectionner plusieurs fichiers dans un champ
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        # Récupère la liste complète des fichiers envoyés via la requête HTTP grâce à "getlist"
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        # On utilise "get" en cas d'ajout d'un seul fichier
        return files.get(name)

    
class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        # Force l'utilisation du widget d'ajout des fichiers personnalisé et active l'attribut multiple par défaut
        kwargs.setdefault("widget", MultipleFileInput(attrs={'class': 'form-control', 'multiple': True}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        # Si plusieurs fichiers on active la validation unitaire standard de Django à chacun d'eux
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        # Si un seul fichier on le valide normalement
        else:
            result = single_file_clean(data, initial)
        return result


# FORMULAIRE DE GESTION DES SINISTRES    
class SinistreForm(forms.ModelForm):
    # Champ personnalisé permettant d'uploader plusieurs fichiers ou pièces justificatives au même moment
    fichiers_justificatifs = MultipleFileField(required=False, label="Pièces justificatives")

    class Meta:
        model = Sinistre
        # Liste des champs du modèle sinistre inclus dans le formulaire de déclaration
        fields = [
            'vehicule', 
            'nom_conducteur',
            'date_survenance', 
            'heure_approximative', 
            'contact_declarant',
            'region', 
            'commune', 
            'ville', 
            'quartier', 
            'circonstances',
            'dommage',
            'autre_vehicule_implique',
            'vehicule_adverse_immatriculation',
            'vehicule_adverse_marque',
            'vehicule_adverse_modele',
            'vehicule_adverse_compagnie',
            'nombre_blesses',
            'nombre_morts',
            'lettre_derogation',
        ]
        
        # Définition des widgets HTML (Classes CSS, Bootstrap, types de champs) pour chaque élément du formulaire
        widgets = {
            'vehicule': forms.Select(attrs={'class': 'form-control'}),
            'nom_conducteur': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du conducteur'}),
            'date_survenance': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'heure_approximative': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'contact_declarant' : forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+228 00 00 00 00'}),            
            'region': forms.Select(attrs={'class': 'form-control'}),
            'commune': forms.Select(attrs={'class': 'form-control'}),
            'ville': forms.Select(attrs={'class': 'form-control'}),
            'quartier': forms.TextInput(attrs={'class': 'form-control'}),
            'circonstances': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'dommage' : forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'autre_vehicule_implique':forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_autre_vehicule'}),
            'vehicule_adverse_immatriculation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Immatriculation du véhicule adverse'}),
            'vehicule_adverse_marque': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Marque'}),
            'vehicule_adverse_modele': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Modèle'}),
            'vehicule_adverse_compagnie': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Compagnie d'assurance du véhicule adverse"}),
            'nombre_blesses': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'nombre_morts': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'lettre_derogation': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_prix_retenu(self):
        # Récupère la valeur du prix saisi par le rédacteur sinistre
        prix_retenu = self.cleaned_data.get('prix_retenu')
        
        # Vérifie si le sinistre existe déjà en base et s'il est rattaché à une quittance
        if self.instance and self.instance.quittance:
            quittance = self.instance.quittance
        return prix_retenu
    
    def __init__(self, *args, **kwargs):
        # Récupération de l'utilisateur passé depuis la vue
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.user = user 
        
        # Si un utilisateur assuré est présent, filtrer ses véhicules
        if user is not None and hasattr(user, 'vehicules'):
            self.fields['vehicule'].queryset = Vehicule.objects.filter(proprietaire=user)
        
        # Texte par défaut dans le menu déroulant des véhicules
        self.fields['vehicule'].empty_label = "Sélectionnez votre véhicule"

def clean(self):
    cleaned_data = super().clean()
    date_survenance = cleaned_data.get('date_survenance')
    assure_profile = getattr(self.user, 'assure', None) if self.user else None
    
    if date_survenance and assure_profile:
        quittance_valide_existe = Quittance.objects.filter(
            contrat=assure_profile,
            date_debut__lte=date_survenance,
            date_fin__lte=date_survenance,
        ).exists()
        
        if not quittance_valide_existe:
            raise forms.ValidationError(
                "Aucun contrat actif n'a été trouvé pour cette date de survenance. "
                "Veuillez vérifier la date, ou contacter votre point mde vente si vous pensez qu'il s'agit d'une erreur."
            )
            
    return cleaned_data


class AjouterNumeroSinistreForm(forms.ModelForm):
    class Meta:
        model = Sinistre
        fields=['numero_sinistre']
        widgets = {
            'numero_sinistre': forms.TextInput({'class': 'form-control', 'placeholder': 'Ex: SIN-2026-001', 'required': 'required'})
        }
        label = {
            'numero_sinistre': 'Nouveau numéro de sinistre',
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['numero_sinistre'].required = True
        
        
class ModifierProfilForm(forms.Form):
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'class': 'form-control'}))
    telephone = forms.CharField(label='Téléphone', max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))        
        
        
class ModifierProfilAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'first_name' : 'Prénom(s)',
            'last_name' : 'Nom',
            'email': 'Email'
        }
        
        
class AgentCreationForm(forms.Form):
    # Champ de création d'un agent
    nom = forms.CharField(max_length=100, label="Nom", widget=forms.TextInput(attrs={'class': 'form-control'}))
    prenom = forms.CharField(max_length=100, label="Prénom", widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=False, label="Email", widget=forms.EmailInput(attrs={'class': 'form-control'}))
    telephone = forms.CharField(max_length=20, required=False, label="Téléphone", widget=forms.TextInput(attrs={'class': 'form-control'}))
    agence = forms.ModelChoiceField(queryset=Agence.objects.all(), label="Point de vente", widget=forms.Select(attrs={'class': 'form-select'}))

    def clean_matricule(self):
        matricule = self.cleaned_data['matricule']
        # Vérifie si le matricule est déjà attribué à un autre agent
        if Agent.objects.filter(matricule=matricule).exists():
            raise forms.ValidationError("Ce matricule existe déjà.")
        return matricule


class ChefCreationForm(forms.Form):
    # Champ de création d'un chef
    nom = forms.CharField(max_length=100, label="Nom", widget=forms.TextInput(attrs={'class': 'form-control'}))
    prenom = forms.CharField(max_length=100, label="Prénom", widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=False, label="Email", widget=forms.EmailInput(attrs={'class': 'form-control'}))
    telephone = forms.CharField(max_length=20, required=False, label="Téléphone", widget=forms.TextInput(attrs={'class': 'form-control'}))
    agence = forms.ModelChoiceField(queryset=Agence.objects.all(), label="Point de vente", widget=forms.Select(attrs={'class': 'form-select'}))

    def clean_matricule(self):
        matricule = self.cleaned_data['matricule']
        # Vérifie si le matricule est déjà attribué à un autre chef
        if ChefDepartement.objects.filter(matricule=matricule).exists():
            raise forms.ValidationError("Ce matricule existe déjà.")
        return matricule
    

class ModifierAgentAdminForm(forms.ModelForm):
    class Meta:
        model = Agent
        # Champ modifiable par l'administrateur pour un agent
        fields = ['matricule', 'telephone', 'agence']
        widgets = {
            'matricule': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'agence': forms.Select(attrs={'class': 'form-control'}),
        }


class ModifierChefAdminForm(forms.ModelForm):
    class Meta:
        model = ChefDepartement
        # Champ modifiable par l'administrateur pour un chef
        fields = ['matricule', 'telephone', 'agence']
        widgets = {
            'matricule': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'agence': forms.Select(attrs={'class': 'form-control'}),
        }


class ModifierSinistreAdminForm(forms.ModelForm):
    class Meta:
        model = Sinistre
        # Champs administratifs/déclaratifs modifiables par l'admin
        # (prix_retenu et les validations restent gérés par leurs actions dédiées)
        fields = [
            'numero_sinistre',
            'statut',
            'nature',
            'agent_traitant',
            'nom_conducteur',
            'contact_declarant',
            'date_survenance',
            'heure_approximative',
            'region',
            'commune',
            'ville',
            'quartier',
            'circonstances',
            'dommage',
            'montant_estime',
            'nombre_blesses',
            'nombre_morts',
            'taux_responsabilite',
        ]
        widgets = {
            'numero_sinistre': forms.TextInput(attrs={'class': 'form-control'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
            'nature': forms.Select(attrs={'class': 'form-control'}),
            'agent_traitant': forms.TextInput(attrs={'class': 'form-control'}),
            'nom_conducteur': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_declarant': forms.TextInput(attrs={'class': 'form-control'}),
            'date_survenance': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'heure_approximative': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'region': forms.Select(attrs={'class': 'form-control'}),
            'commune': forms.Select(attrs={'class': 'form-control'}),
            'ville': forms.Select(attrs={'class': 'form-control'}),
            'quartier': forms.TextInput(attrs={'class': 'form-control'}),
            'circonstances': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'dommage': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'montant_estime': forms.NumberInput(attrs={'class': 'form-control'}),
            'nombre_blesses': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'nombre_morts': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'taux_responsabilite': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pré-remplit correctement le champ datetime-local à partir de la valeur existante
        if self.instance and self.instance.date_survenance:
            self.initial['date_survenance'] = self.instance.date_survenance.strftime('%Y-%m-%dT%H:%M')
            
            
class DemanderComplementsForm(forms.Form):
    # Champ de texte pour rédiger le motif des pièces manquantes à réclamer à l'assuré
    motif = forms.CharField(
        label="Précisez les éléments manquants",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
    )


class MarquerConformeForm(forms.Form):
    # Champ permettant de valider le prix retenu lors du marquage conforme d'un sinistre
    prix_retenu = forms.DecimalField(
        label="Prix retenu (FCFA)",
        max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
    )


class IndemnisationForm(forms.Form):
    # Recense les informations du bénéficiaire et du chèque d'indemnisation
    beneficiaire_nom = forms.CharField(label="Nom du bénéficiaire",widget=forms.TextInput(attrs={'class': 'form-control'}))
    beneficiaire_prenoms = forms.CharField(label="Prénoms du bénéficiaire",widget=forms.TextInput(attrs={'class': 'form-control'}))
    beneficiaire_telephone = forms.CharField(label="Téléphone du bénéficiaire",widget=forms.TextInput(attrs={'class': 'form-control'}))
    numero_cheque = forms.CharField(label="Numéro de chèque",widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: CHK-2026-001'}))
    banque_cheque = forms.CharField(label="Banque émettrice",widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Ecobank'}))
    montant_cheque = forms.DecimalField(label="Montant versé (FCFA)",max_digits=12, decimal_places=2,widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}))
    date_emission_cheque = forms.DateField(label="Date d'émission du chèque",widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))

    def __init__(self, *args, **kwargs):
        # Récupération du sinistre passé depuis la vue
        self.sinistre = kwargs.pop('sinistre', None)
        super().__init__(*args, **kwargs)
        
        # Pré-remplissage du montant si le prix retenu existe
        if self.sinistre and self.sinistre.prix_retenu:
            self.fields['montant_cheque'].initial = self.sinistre.prix_retenu
            self.fields['date_emission_cheque'].initial = timezone.now().date()

    def clean_montant_cheque(self):
        montant = self.cleaned_data.get('montant_cheque')
        # Vérifie que le montant du chèque ne dépasse pas la valeur du prix retenu sur le sinistre
        if self.sinistre and self.sinistre.prix_retenu:
            if montant > self.sinistre.prix_retenu:
                raise forms.ValidationError(
                    f"Le montant du chèque ({montant} FCFA) ne peut pas dépasser le prix retenu ({self.sinistre.prix_retenu} FCFA)."
                )
        return montant
    

class SansSuiteForm(forms.Form):
    # Champ permettant de rédiger le motif de classement d'un dossier sans suite
    motif = forms.CharField(
        label="Motif du classement sans suite",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
    )


class ImportExcelForm(forms.Form):
    # Champ fichier unique pour téléverser un fichier Excel (.xlsx)
    fichier = forms.FileField(label="Fichier Excel des contrats (.xlsx)")


class ImportSinistresForm(forms.Form):
    fichier = forms.FileField(label="Fichier Excel des sinistres (.xlsx)")
    
    
class AssureAdminForm(forms.ModelForm):
    # Champs supplémentaires pour manipuler directement le profil utilisateur django lié à l'assuré
    first_name = forms.CharField(label="Prénom", widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(label="Nom", widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Assure
        fields = ['numero_police', 'telephone']
        widgets = {
            'numero_police': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pré-remplit les champs prénom, nom et email à partir de l'objet User associé à l'assuré
        if self.instance and self.instance.pk and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        assure = super().save(commit=False)
        # Met à jour et sauvegarde également l'objet utilisateur Django lié
        if assure.user:
            assure.user.first_name = self.cleaned_data['first_name']
            assure.user.last_name = self.cleaned_data['last_name']
            assure.user.email = self.cleaned_data['email']
            if commit:
                assure.user.save()
        if commit:
            assure.save()
        return assure


class ChequeForm(forms.ModelForm):
    # Champ du modèle Cheque
    class Meta:
        model = Cheque
        fields = [
            'numero_cheque', 
            'banque_emettrice', 
            'montant', 
            'beneficiaire', 
            'date_disponibilite', 
            'statut'
        ]
        widgets = {
            'numero_cheque': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: CHK-2026-00123'}),
            'banque_emettrice': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Ecobank / Orabank'}),
            'montant': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'beneficiaire': forms.TextInput(attrs={'class': 'form-control'}),
            'date_disponibilite': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'statut': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        # Récupération de l'instance du sinistre passée depuis la vue
        self.sinistre = kwargs.pop('sinistre', None)
        super().__init__(*args, **kwargs)

        if self.sinistre:
            # Pré-remplissage du montant avec le prix retenu du sinistre
            if not self.initial.get('montant') and self.sinistre.prix_retenu is not None:
                self.fields['montant'].initial = self.sinistre.prix_retenu

            # Pré-remplissage du nom du bénéficiaire
            if not self.initial.get('beneficiaire') and self.sinistre.assure:
                user_assure = self.sinistre.assure
                nom_complet = f"{user_assure.last_name} {user_assure.first_name}".strip()
                self.fields['beneficiaire'].initial = nom_complet if nom_complet else user_assure.username

    def clean_montant(self):
        montant = self.cleaned_data.get('montant')
        # Le montant du chèque ne doit pas dépasser le prix retenu du sinistre
        if self.sinistre and self.sinistre.prix_retenu is not None:
            if montant > self.sinistre.prix_retenu:
                raise forms.ValidationError(
                    f"Le montant du chèque ({montant} FCFA) ne peut pas être supérieur au prix retenu ({self.sinistre.prix_retenu} FCFA)."
                )
        return montant


class EsinistreAuthentificationForm(AuthenticationForm):
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username:
            profil = get_profil_par_identifiant(username)
            
            # Vérifier si le compte est déjà bloqué et bloquer immédiatement la tentative si oui
            if profil_est_bloque(profil):
                raise forms.ValidationError(
                    "Vous avez atteint 3 tentatives infructueuses. Votre compte est bloqué. "
                    "Veuillez cliquer sur « Mot de passe oublié ? » pour le réactiver.",
                    code='compte_bloque',
                )

        # Laisser Django effectuer sa validation normale (Vérfication du mot de passe)
        try:
            cleaned_data = super().clean()
        except forms.ValidationError:
            # Si Django refuse l'authentification (mauvais mot de passe), on enregistre l'échec et on incrémente les tentatives
            if username:
                enregistrer_echec(username)
                
                # On vérifie immédiatement si cet échec vient de bloquer le compte
                profil_mis_a_jour = get_profil_par_identifiant(username)
                if profil_mis_a_jour and profil_est_bloque(profil_mis_a_jour):
                    raise forms.ValidationError(
                        "Vous avez atteint 3 tentatives infructueuses. Votre compte est bloqué. "
                        "Veuillez cliquer sur « Mot de passe oublié ? » pour le réactiver.",
                        code='compte_bloque',
                    )
            raise

        # Si la connexion réussit, on remet le compteur à zéro
        if username:
            profil = get_profil_par_identifiant(username)
            reinitialiser_tentatives(profil)

        return cleaned_data
            

class MotDePasseOublieForm(forms.Form):
    # Champs pour identifier l'utilisateur lors de la demande de réinitialisation de mot de passe
    identifiant = forms.CharField(label="N° de police / Identifiant",widget=forms.TextInput(attrs={'class': 'form-control'}))
    telephone = forms.CharField(label="Téléphone enregistré",widget=forms.TextInput(attrs={'class': 'form-control'}))


# GESTION DE LA SITUATION GEOGRAPHIQUE
class RegionForm(forms.ModelForm):
    class Meta:
        model = Region
        fields = ['nom']
        widgets = {'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom de la région'})}


class CommuneForm(forms.ModelForm):
    class Meta:
        model = Commune
        # Rattache une commune à une région
        fields = ['region', 'nom']
        widgets = {
            'region':forms.Select(attrs={'class': 'form-select'}),
            'nom': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Nom de la commune'}),
        }


class VilleForm(forms.ModelForm):
    class Meta:
        model = Ville
        # Rattache une ville à une commune
        fields = ['commune', 'nom']
        widgets = {
            'commune': forms.Select(attrs={'class': 'form-select'}),
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom de la ville'}),
        }


class RetraitChequeForm(forms.Form):
    
    #Formulaire de tracabilité pour le retrait physique d'un chèque
    nom_retirant = forms.CharField(label="Nom du retirant", required=False,widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Laisser vide si c'est le bénéficiaire"}))
    type_piece_retirant = forms.ChoiceField(label="Type de pièce", choices=Paiement.TYPE_PIECE_CHOICES,widget= forms.Select(attrs={'class': 'form-select'}))
    numero_piece_retirant = forms.CharField(label="N° de la pièce",widget= forms.TextInput(attrs={'class': 'form-control'}))
    piece_identite_retirant = forms.FileField(label="Scan/Photo de la pièce",widget= forms.ClearableFileInput(attrs={'class': 'form-control'}))


class AgenceForm(forms.ModelForm):
    # Permet de lier une agence physique à une ville spécifique
    ville = forms.ModelChoiceField(
        queryset=Ville.objects.all(),
        label="Ville",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Agence
        fields = ['nom', 'ville']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Nom du point de vente"}),
        }