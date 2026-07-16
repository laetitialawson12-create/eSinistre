from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone
from datetime import timedelta
from .models import Sinistre, PieceJointe


def jours_ouvres_entre(date_debut, date_fin):
    """Compte le nombre de jours ouvrés (lundi-vendredi) entre deux dates, bornes exclues."""
    jours = 0
    date_courante = date_debut
    while date_courante < date_fin:
        date_courante += timedelta(days=1)
        if date_courante.weekday() < 5:  # 0=lundi ... 4=vendredi
            jours += 1
    return jours


class SinistreForm(forms.ModelForm):
    class Meta:
        model = Sinistre
        fields = [
            'region', 'ville', 'prefecture', 'quartier', 'precision', 
            'date_survenance', 'heure_approximative', 'nature', 
            'vehicule', 'circonstances', 'lettre_derogation'
        ]
        widgets = {
            'date_survenance': forms.DateTimeInput(attrs={'type': 'date', 'class': 'form-control'}),
            'heure_approximative': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'circonstances': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'precision': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Décrivez les circonstances...'}),
            'region': forms.Select(attrs={'class': 'form-control'}),
            'ville': forms.Select(attrs={'class': 'form-control'}),
            'prefecture': forms.Select(attrs={'class': 'form-control'}),
            'quartier': forms.TextInput(attrs={'class': 'form-control'}),
            'nature': forms.Select(attrs={'class': 'form-control'}),
            'vehicule': forms.Select(attrs={'class': 'form-control'}),
            'lettre_derogation': forms.FileInput(attrs={'class': 'form-control'})
        }
        labels = {
            'date_survenance': 'Date du sinistre',
            'heure_approximative': 'Heure approximative',
            'nature': 'Nature du sinistre',
            'precision': 'Détails des circonstances',
            'lettre_derogation': 'Lettre de dérogation (si délai dépassé)'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['quartier'].required = True
        self.fields['vehicule'].required = True
        self.fields['lettre_derogation'].required = False

    def clean(self):
        cleaned_data = super().clean()
        date_survenance = cleaned_data.get("date_survenance")
        lettre = cleaned_data.get("lettre_derogation")

        if date_survenance:
            date_ref = date_survenance.date() if hasattr(date_survenance, 'date') else date_survenance
            aujourdhui = timezone.now().date()

            if date_ref <= aujourdhui:
                jours_ouvres = jours_ouvres_entre(date_ref, aujourdhui)
                if jours_ouvres > 5 and not lettre:
                    raise forms.ValidationError({'lettre_derogation': "Le délai de 5 jours ouvrés est dépassé. Veuillez fournir une lettre de dérogation."})
        return cleaned_data

PieceJointeFormSet = inlineformset_factory(
    Sinistre,
    PieceJointe,
    fields=('fichier',),
    extra=3,
    can_delete=True,
    widgets={'fichier': forms.FileInput(attrs={'class': 'form-control mt-2'})}
)