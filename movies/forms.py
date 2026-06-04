from django import forms

from .models import Commentaire, Critique


class ReviewForm(forms.ModelForm):
    """Formulaire public de publication et de modification d'une critique."""

    # Ce formulaire est destiné aux utilisateurs du site côté public.
    #
    # Il permet :
    # - de publier une nouvelle critique sur un film ;
    # - de modifier une critique existante ;
    # - de contrôler les champs visibles par l'utilisateur ;
    # - d'appliquer une validation spécifique aux champs titre et texte.
    #
    # Il hérite de forms.ModelForm, ce qui signifie que Django construit
    # automatiquement une partie du formulaire à partir du modèle Critique.

    class Meta:
        # Modèle Django associé à ce formulaire.
        #
        # Les données validées par ce formulaire permettront de créer
        # ou modifier une instance de Critique.
        model = Critique

        # Champs du modèle Critique exposés dans le formulaire public.
        #
        # Les autres champs importants, comme le film et l'utilisateur,
        # ne sont pas demandés directement à l'utilisateur.
        #
        # Ils doivent normalement être définis côté vue afin d'éviter
        # qu'un utilisateur puisse publier une critique au nom de quelqu'un d'autre
        # ou l'associer à un mauvais film.
        fields = ("titre", "texte", "note")

        # Libellés affichés dans le formulaire HTML.
        #
        # Ces labels remplacent les noms techniques des champs du modèle
        # par des textes plus clairs pour l'utilisateur final.
        labels = {
            "titre": "Titre de votre critique",
            "texte": "Votre analyse",
            "note": "Votre note",
        }

        # Textes d'aide affichés sous les champs du formulaire.
        #
        # Ils guident l'utilisateur pour remplir correctement sa critique.
        help_texts = {
            "titre": "Résumez votre avis en quelques mots.",
            "texte": "Argumentez votre point de vue et partagez ce qui vous a marqué.",
            "note": "Choisissez une note entre 1 et 5.",
        }

        # Messages d'erreur personnalisés.
        #
        # Ils permettent d'afficher des erreurs compréhensibles et adaptées
        # au vocabulaire de l'application Movie Review.
        error_messages = {
            "titre": {
                # Message affiché si aucun titre n'est fourni.
                "required": "Le titre de la critique est obligatoire.",

                # Message affiché si le titre dépasse la longueur maximale
                # définie dans le modèle Critique.
                "max_length": "Le titre de la critique est trop long.",
            },
            "texte": {
                # Message affiché si le texte de critique est absent.
                "required": "Le texte de la critique est obligatoire.",
            },
            "note": {
                # Message affiché si aucune note n'est sélectionnée.
                "required": "Vous devez attribuer une note.",

                # Message affiché si la valeur de note ne correspond pas
                # aux choix autorisés.
                "invalid_choice": "Choisissez une note valide entre 1 et 5.",
            },
        }

        # Personnalisation des widgets HTML utilisés pour chaque champ.
        #
        # Les widgets permettent de contrôler le type d'élément HTML généré
        # ainsi que ses attributs CSS ou d'affichage.
        widgets = {
            "titre": forms.TextInput(
                attrs={
                    # Classe CSS utilisée pour harmoniser le style du champ
                    # avec le reste de l'interface.
                    "class": "form-control",

                    # Exemple affiché dans le champ avant saisie.
                    "placeholder": "Ex. Une œuvre magistrale",
                }
            ),
            "texte": forms.Textarea(
                attrs={
                    # Classe CSS commune aux champs du projet.
                    "class": "form-control",

                    # Hauteur visuelle de la zone de texte.
                    # rows=8 donne assez d'espace pour rédiger une critique détaillée.
                    "rows": 8,

                    # Texte indicatif affiché avant saisie.
                    "placeholder": "Partagez votre avis sur ce film...",
                }
            ),
            "note": forms.Select(
                # Liste des choix affichés dans le menu déroulant.
                #
                # Le premier choix vide force l'utilisateur à sélectionner
                # volontairement une note.
                choices=[
                    ("", "Choisir une note"),
                    (1, "1/5"),
                    (2, "2/5"),
                    (3, "3/5"),
                    (4, "4/5"),
                    (5, "5/5"),
                ],

                # Classe CSS appliquée au select.
                attrs={"class": "form-control"},
            ),
        }

    def clean_titre(self):
        # Méthode de validation personnalisée du champ titre.
        #
        # Django appelle automatiquement clean_titre() pendant la validation
        # du formulaire, après la validation de base du champ.
        #
        # Cette méthode sert ici à éviter qu'un titre contenant uniquement
        # des espaces soit accepté.

        # Récupère le titre validé par Django puis supprime les espaces
        # au début et à la fin.
        titre = self.cleaned_data["titre"].strip()

        # Si le titre est vide après suppression des espaces,
        # on considère qu'il est invalide.
        if not titre:
            raise forms.ValidationError("Le titre de la critique est obligatoire.")

        # Retourne le titre nettoyé.
        #
        # La valeur retournée remplacera la valeur originale dans cleaned_data.
        return titre

    def clean_texte(self):
        # Méthode de validation personnalisée du champ texte.
        #
        # Elle empêche l'utilisateur de publier une critique vide
        # ou composée uniquement d'espaces.

        # Récupère le texte validé par Django puis retire les espaces inutiles
        # au début et à la fin.
        texte = self.cleaned_data["texte"].strip()

        # Si le texte devient vide après nettoyage,
        # le formulaire doit afficher une erreur.
        if not texte:
            raise forms.ValidationError("Le texte de la critique est obligatoire.")

        # Retourne le texte nettoyé.
        return texte


class CommentForm(forms.ModelForm):
    """Formulaire public de publication d'un commentaire sur une critique."""

    # Ce formulaire est utilisé pour permettre à un utilisateur connecté
    # de commenter une critique publiée par lui-même ou par un autre utilisateur,
    # selon les règles définies dans les vues.
    #
    # Il expose uniquement le champ texte.
    #
    # Les champs comme :
    # - la critique commentée ;
    # - l'utilisateur auteur du commentaire ;
    # - la date de publication ;
    # ne doivent pas être saisis directement par l'utilisateur.
    # Ils sont normalement définis côté vue ou automatiquement par le modèle.

    class Meta:
        # Modèle Django associé à ce formulaire.
        model = Commentaire

        # Seul le texte du commentaire est demandé à l'utilisateur.
        fields = ("texte",)

        # Libellé affiché au-dessus du champ.
        labels = {"texte": "Votre commentaire"}

        # Messages d'erreur personnalisés pour le champ texte.
        error_messages = {
            "texte": {
                # Message affiché si l'utilisateur tente d'envoyer
                # un commentaire vide.
                "required": "Le commentaire ne peut pas être vide.",
            }
        }

        # Widget HTML utilisé pour le commentaire.
        widgets = {
            "texte": forms.Textarea(
                attrs={
                    # Classe CSS commune aux champs du projet.
                    "class": "form-control",

                    # Hauteur de la zone de saisie.
                    # rows=3 convient à un commentaire généralement plus court
                    # qu'une critique complète.
                    "rows": 3,

                    # Texte indicatif affiché dans le champ vide.
                    "placeholder": "Partagez votre commentaire...",
                }
            )
        }

    def clean_texte(self):
        # Méthode de validation personnalisée du texte du commentaire.
        #
        # Elle complète la validation "required" standard de Django
        # en refusant aussi les commentaires composés uniquement d'espaces.

        # Récupère le texte saisi puis supprime les espaces en début et fin.
        texte = self.cleaned_data["texte"].strip()

        # Si le texte est vide après nettoyage,
        # le commentaire doit être refusé.
        if not texte:
            raise forms.ValidationError("Le commentaire ne peut pas être vide.")

        # Retourne le texte nettoyé.
        return texte