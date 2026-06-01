from django import forms

from .models import Commentaire


class CommentForm(forms.ModelForm):
    """Formulaire public de publication d'un commentaire sur une critique."""

    class Meta:
        model = Commentaire
        fields = ("texte",)
        labels = {"texte": "Votre commentaire"}
        error_messages = {
            "texte": {
                "required": "Le commentaire ne peut pas être vide.",
            }
        }
        widgets = {
            "texte": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Partagez votre commentaire...",
                }
            )
        }

    def clean_texte(self):
        texte = self.cleaned_data["texte"].strip()
        if not texte:
            raise forms.ValidationError("Le commentaire ne peut pas être vide.")
        return texte
