from django import forms
from django.utils import timezone
from datetime import timedelta
from .models import Sinistre, Agent, Agence, ChefDepartement, Assure, Quittance, Vehicule, Cheque
from django.contrib.auth.models import User


def jours_ouvres_entre(date_debut, date_fin):
    jours = 0
    date_courante = date_debut
    while date_courante < date_fin:
        date_courante += timedelta(days=1)
        if date_courante.weekday() < 5:
            jours += 1
    return jours


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={'class': 'form-control', 'multiple': True}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

    
class SinistreForm(forms.ModelForm):
    fichiers_justificatifs = MultipleFileField(required=False, label="Pièces justificatives")

    class Meta:
        model = Sinistre
        fields = [
            'vehicule', 
            'nom_conducteur',
            'date_survenance', 
            'heure_approximative', 
            'nature', 
            'region', 
            'ville', 
            'prefecture', 
            'quartier', 
            'circonstances',
            'prix_retenu',
            'agent_traitant'
        ]
        widgets = {
            'vehicule': forms.Select(attrs={'class': 'form-control'}),
            'nom_conducteur': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du conducteur'}),
            'date_survenance': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'heure_approximative': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'nature': forms.Select(attrs={'class': 'form-control'}),
            'region': forms.Select(attrs={'class': 'form-control'}),
            'ville': forms.Select(attrs={'class': 'form-control'}),
            'prefecture': forms.Select(attrs={'class': 'form-control'}),
            'quartier': forms.TextInput(attrs={'class': 'form-control'}),
            'circonstances': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'prix_retenu': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Prix retenu en FCFA'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
            'agent_traitant': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_prix_retenu(self):
        prix_retenu = self.cleaned_data.get('prix_retenu')
        
        # Récupération de l'instance du sinistre en cours d'édition
        if self.instance and self.instance.quittance:
            quittance = self.instance.quittance
            
            if prix_retenu is not None and quittance.prime is not None:
                if prix_retenu > quittance.prime:
                    raise forms.ValidationError(
                        f"Le prix retenu ({prix_retenu} FCFA) ne peut pas dépasser la prime de la quittance ({quittance.prime} FCFA)."
                    )
        
        return prix_retenu
    
    def __init__(self, *args, **kwargs):
        # Récupération de l'utilisateur passé depuis la vue
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Si un utilisateur assuré est présent, filtrer ses véhicules
        if user is not None and hasattr(user, 'vehicules'):
            self.fields['vehicule'].queryset = Vehicule.objects.filter(proprietaire=user)
        
        self.fields['vehicule'].empty_label = "Sélectionnez votre véhicule"


class ModifierProfilForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'email': 'Email',
        }
        

class AgentCreationForm(forms.Form):
    matricule = forms.CharField(max_length=20, label="Matricule", widget=forms.TextInput(attrs={'class': 'form-control'}))
    nom = forms.CharField(max_length=100, label="Nom", widget=forms.TextInput(attrs={'class': 'form-control'}))
    prenom = forms.CharField(max_length=100, label="Prénom", widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=False, label="Email", widget=forms.EmailInput(attrs={'class': 'form-control'}))
    telephone = forms.CharField(max_length=20, required=False, label="Téléphone", widget=forms.TextInput(attrs={'class': 'form-control'}))
    agence = forms.ModelChoiceField(queryset=Agence.objects.all(), label="Agence", widget=forms.Select(attrs={'class': 'form-select'}))

    def clean_matricule(self):
        matricule = self.cleaned_data['matricule']
        if Agent.objects.filter(matricule=matricule).exists():
            raise forms.ValidationError("Ce matricule existe déjà.")
        return matricule


class ChefCreationForm(forms.Form):
    matricule = forms.CharField(max_length=20, label="Matricule", widget=forms.TextInput(attrs={'class': 'form-control'}))
    nom = forms.CharField(max_length=100, label="Nom", widget=forms.TextInput(attrs={'class': 'form-control'}))
    prenom = forms.CharField(max_length=100, label="Prénom", widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=False, label="Email", widget=forms.EmailInput(attrs={'class': 'form-control'}))
    telephone = forms.CharField(max_length=20, required=False, label="Téléphone", widget=forms.TextInput(attrs={'class': 'form-control'}))
    agence = forms.ModelChoiceField(queryset=Agence.objects.all(), label="Agence", widget=forms.Select(attrs={'class': 'form-select'}))

    def clean_matricule(self):
        matricule = self.cleaned_data['matricule']
        if ChefDepartement.objects.filter(matricule=matricule).exists():
            raise forms.ValidationError("Ce matricule existe déjà.")
        return matricule
    

class ModifierAgentAdminForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ['matricule', 'telephone', 'agence']
        widgets = {
            'matricule': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'agence': forms.Select(attrs={'class': 'form-control'}),
        }


class ModifierChefAdminForm(forms.ModelForm):
    class Meta:
        model = ChefDepartement
        fields = ['matricule', 'telephone', 'agence']
        widgets = {
            'matricule': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'agence': forms.Select(attrs={'class': 'form-control'}),
        }

        
class DemanderComplementsForm(forms.Form):
    motif = forms.CharField(
        label="Précisez les éléments manquants",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
    )


class MarquerConformeForm(forms.Form):
    prix_retenu = forms.DecimalField(
        label="Prix retenu (FCFA)",
        max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
    )


class IndemnisationForm(forms.Form):
    beneficiaire_nom = forms.CharField(
        label="Nom du bénéficiaire",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    beneficiaire_prenoms = forms.CharField(
        label="Prénoms du bénéficiaire",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    beneficiaire_telephone = forms.CharField(
        label="Téléphone du bénéficiaire",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    numero_cheque = forms.CharField(
        label="Numéro de chèque",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: CHK-2026-001'}),
    )
    banque_cheque = forms.CharField(
        label="Banque émettrice",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Ecobank'}),
    )
    montant_cheque = forms.DecimalField(
        label="Montant versé (FCFA)",
        max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
    )
    date_emission_cheque = forms.DateField(
        label="Date d'émission du chèque",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )

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
        if self.sinistre and self.sinistre.prix_retenu:
            if montant > self.sinistre.prix_retenu:
                raise forms.ValidationError(
                    f"Le montant du chèque ({montant} FCFA) ne peut pas dépasser le prix retenu ({self.sinistre.prix_retenu} FCFA)."
                )
        return montant
    

class SansSuiteForm(forms.Form):
    motif = forms.CharField(
        label="Motif du classement sans suite",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
    )


class ImportExcelForm(forms.Form):
    fichier = forms.FileField(label="Fichier Excel des contrats (.xlsx)")


class AssureAdminForm(forms.ModelForm):
    # Champs de l'utilisateur lié
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
        if self.instance and self.instance.pk and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        assure = super().save(commit=False)
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
            # 1. Pré-remplissage du montant avec le prix retenu du sinistre
            if not self.initial.get('montant') and self.sinistre.prix_retenu is not None:
                self.fields['montant'].initial = self.sinistre.prix_retenu

            # 2. Pré-remplissage du nom du bénéficiaire
            if not self.initial.get('beneficiaire') and self.sinistre.assure:
                user_assure = self.sinistre.assure
                nom_complet = f"{user_assure.last_name} {user_assure.first_name}".strip()
                self.fields['beneficiaire'].initial = nom_complet if nom_complet else user_assure.username

    def clean_montant(self):
        montant = self.cleaned_data.get('montant')
        # Vérification logique : le chèque ne doit pas dépasser le prix retenu du sinistre
        if self.sinistre and self.sinistre.prix_retenu is not None:
            if montant > self.sinistre.prix_retenu:
                raise forms.ValidationError(
                    f"Le montant du chèque ({montant} FCFA) ne peut pas être supérieur au prix retenu ({self.sinistre.prix_retenu} FCFA)."
                )
        return montant