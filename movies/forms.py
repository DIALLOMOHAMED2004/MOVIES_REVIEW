from django import forms

from .models import Commentaire, Critique


class ReviewForm(forms.ModelForm):
    """Formulaire public de publication et de modification d'une critique."""

    class Meta:
        model = Critique
        fields = ("titre", "texte", "note")
        labels = {
            "titre": "Titre de votre critique",
            "texte": "Votre analyse",
            "note": "Votre note",
        }
        help_texts = {
            "titre": "Résumez votre avis en quelques mots.",
            "texte": "Argumentez votre point de vue et partagez ce qui vous a marqué.",
            "note": "Choisissez une note entre 1 et 5.",
        }
        error_messages = {
            "titre": {
                "required": "Le titre de la critique est obligatoire.",
                "max_length": "Le titre de la critique est trop long.",
            },
            "texte": {
                "required": "Le texte de la critique est obligatoire.",
            },
            "note": {
                "required": "Vous devez attribuer une note.",
                "invalid_choice": "Choisissez une note valide entre 1 et 5.",
            },
        }
        widgets = {
            "titre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex. Une œuvre magistrale",
                }
            ),
            "texte": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 8,
                    "placeholder": "Partagez votre avis sur ce film...",
                }
            ),
            "note": forms.Select(
                choices=[
                    ("", "Choisir une note"),
                    (1, "1/5"),
                    (2, "2/5"),
                    (3, "3/5"),
                    (4, "4/5"),
                    (5, "5/5"),
                ],
                attrs={"class": "form-control"},
            ),
        }

    def clean_titre(self):
        titre = self.cleaned_data["titre"].strip()
        if not titre:
            raise forms.ValidationError("Le titre de la critique est obligatoire.")
        return titre

    def clean_texte(self):
        texte = self.cleaned_data["texte"].strip()
        if not texte:
            raise forms.ValidationError("Le texte de la critique est obligatoire.")
        return texte


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
