from django import forms
from django.utils import timezone
from datetime import timedelta
from .models import Sinistre
from django.contrib.auth.models import User


def jours_ouvres_entre(date_debut, date_fin):
    jours = 0
    date_courante = date_debut
    while date_courante < date_fin:
        date_courante += timedelta(days=1)
        if date_courante.weekday() < 5:
            jours += 1
    return jours

class SinistreForm(forms.ModelForm):
    # Champ de fichier simple, sans contrainte de widget complexe
    fichiers_justificatifs = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        required=False,
        label="Pièces justificatives"
    )

    class Meta:
        model = Sinistre
        fields = [
            'region', 'ville', 'prefecture', 'quartier', 'precision', 
            'date_survenance', 'heure_approximative', 'nature', 
            'vehicule', 'circonstances', 'lettre_derogation',
            'n_police', 'nom_conducteur', 'immatriculation',
            'fichiers_justificatifs'
        ]
        widgets = {
            'date_survenance': forms.DateTimeInput(attrs={'type': 'date', 'class': 'form-control'}),
            'heure_approximative': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'circonstances': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'precision': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'region': forms.Select(attrs={'class': 'form-control'}),
            'ville': forms.Select(attrs={'class': 'form-control'}),
            'prefecture': forms.Select(attrs={'class': 'form-control'}),
            'quartier': forms.TextInput(attrs={'class': 'form-control'}),
            'nature': forms.Select(attrs={'class': 'form-control'}),
            'vehicule': forms.Select(attrs={'class': 'form-control'}),
            'lettre_derogation': forms.FileInput(attrs={'class': 'form-control'}),
            'n_police': forms.TextInput(attrs={'class': 'form-control'}),
            'immatriculation': forms.TextInput(attrs={'class': 'form-control'}),
            'nom_conducteur': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # On force l'attribut multiple ici pour éviter l'erreur au démarrage
        self.fields['fichiers_justificatifs'].widget.attrs.update({'multiple': True})
        self.fields['quartier'].required = True
        self.fields['vehicule'].required = True
        if self.user and self.user.is_authenticated:
            self.fields['vehicule'].queryset = self.user.vehicules.all()

    def clean(self):
        cleaned_data = super().clean()
        date_survenance = cleaned_data.get("date_survenance")
        lettre = cleaned_data.get("lettre_derogation")
        if date_survenance:
            date_ref = date_survenance.date() if hasattr(date_survenance, 'date') else date_survenance
            aujourdhui = timezone.now().date()
            if date_ref <= aujourdhui:
                if jours_ouvres_entre(date_ref, aujourdhui) > 5 and not lettre:
                    raise forms.ValidationError({'lettre_derogation': "Le délai de 5 jours est dépassé."})
        return cleaned_data
    

class ModifierProfilForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']