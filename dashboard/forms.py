from django import forms

from movies.models import Acteur, Casting, Film, Genre


class DashboardModelForm(forms.ModelForm):
    # Formulaire de base utilisé par les formulaires du dashboard personnalisé.
    #
    # L'objectif de cette classe est d'éviter de répéter le même code de style
    # dans FilmForm, GenreForm et ActeurForm.
    #
    # Tous les formulaires qui héritent de DashboardModelForm bénéficient donc
    # automatiquement d'une mise en forme commune pour leurs champs HTML.
    def __init__(self, *args, **kwargs):
        # Appelle le constructeur parent de ModelForm.
        # Cette étape est indispensable pour que Django construise les champs
        # du formulaire à partir du modèle associé.
        super().__init__(*args, **kwargs)

        # Parcourt tous les champs générés par Django dans le formulaire.
        for field in self.fields.values():

            # On évite d'ajouter la classe "form-control" aux cases à cocher.
            # Les checkbox ont souvent un style HTML/CSS différent des champs texte,
            # select, textarea ou input classiques.
            if not isinstance(field.widget, forms.CheckboxInput):

                # Ajoute la classe CSS "form-control" uniquement si elle n'existe pas déjà.
                #
                # setdefault est important ici :
                # - si le widget possède déjà une classe CSS définie ailleurs,
                #   elle n'est pas écrasée ;
                # - si aucune classe n'est définie, "form-control" est ajoutée.
                #
                # Cela permet d'uniformiser l'apparence des formulaires du dashboard
                # tout en respectant les personnalisations déjà définies dans certains widgets.
                field.widget.attrs.setdefault("class", "form-control")


class FilmForm(DashboardModelForm):
    # Formulaire utilisé dans le dashboard pour créer ou modifier un film.
    #
    # Il hérite de DashboardModelForm afin de récupérer automatiquement
    # la mise en forme commune des champs du dashboard.

    # Champ personnalisé permettant d'associer plusieurs acteurs à un film.
    #
    # Ce champ ne correspond pas directement à un champ simple du modèle Film.
    # Il sert plutôt d'interface pratique pour gérer la relation entre Film et Acteur
    # via le modèle intermédiaire Casting.
    acteurs = forms.ModelMultipleChoiceField(
        # Liste des acteurs disponibles dans le champ de sélection multiple.
        queryset=Acteur.objects.all(),

        # Le champ n'est pas obligatoire :
        # un film peut être créé sans acteur associé.
        required=False,

        # Libellé affiché dans le formulaire.
        label="Acteurs",

        # Widget HTML utilisé pour sélectionner plusieurs acteurs.
        # SelectMultiple génère une liste de sélection multiple.
        widget=forms.SelectMultiple(attrs={"class": "form-control"}),

        # Texte d'aide affiché sous le champ.
        help_text="Sélectionnez les acteurs déjà créés à associer au film.",
    )

    class Meta:
        # Modèle Django associé à ce formulaire.
        # FilmForm permet donc de créer ou modifier des instances de Film.
        model = Film

        # Liste des champs affichés dans le formulaire.
        #
        # Les champs titre, synopsis, genre, date_sortie, duree_minutes et affiche
        # appartiennent au modèle Film.
        #
        # Le champ acteurs est déclaré manuellement plus haut pour faciliter
        # la gestion des acteurs associés au film.
        fields = (
            "titre",
            "synopsis",
            "genre",
            "date_sortie",
            "duree_minutes",
            "affiche",
            "acteurs",
        )

        # Personnalisation de certains widgets HTML.
        widgets = {
            # Champ de date affiché sous forme de sélecteur de date HTML5.
            #
            # Le format "%Y-%m-%d" correspond au format attendu par les inputs
            # HTML de type date.
            "date_sortie": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),

            # Champ synopsis affiché sous forme de zone de texte plus grande.
            # rows=6 donne suffisamment d'espace pour rédiger un résumé de film.
            "synopsis": forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, **kwargs):
        # Initialise d'abord le formulaire parent.
        #
        # Cela construit tous les champs définis par ModelForm et applique aussi
        # la logique de DashboardModelForm, notamment l'ajout de la classe CSS
        # "form-control" aux champs concernés.
        super().__init__(*args, **kwargs)

        # Recharge explicitement la liste des acteurs disponibles.
        #
        # Cela garantit que le champ acteurs utilise les données les plus récentes
        # de la base au moment où le formulaire est instancié.
        self.fields["acteurs"].queryset = Acteur.objects.all()

        # Si le formulaire modifie un film existant,
        # on préremplit le champ acteurs avec les acteurs déjà liés à ce film.
        #
        # self.instance.pk permet de savoir si l'instance existe déjà en base.
        if self.instance.pk:
            self.fields["acteurs"].initial = self.instance.acteurs.all()

    def sync_casting(self, film):
        # Synchronise les acteurs sélectionnés dans le formulaire avec
        # les enregistrements Casting réellement présents en base.
        #
        # Cette méthode doit être appelée après l'enregistrement du film,
        # car elle a besoin d'une instance Film existante.
        #
        # Elle met à jour la table intermédiaire Casting :
        # - suppression des castings retirés dans le formulaire ;
        # - création des nouveaux castings ajoutés dans le formulaire ;
        # - conservation des castings déjà existants.

        # Récupère les identifiants des acteurs sélectionnés dans le formulaire.
        #
        # self.cleaned_data["acteurs"] contient un QuerySet d'instances Acteur
        # validées par le champ ModelMultipleChoiceField.
        #
        # values_list("id", flat=True) extrait uniquement les IDs.
        # set(...) permet ensuite de comparer facilement les sélections.
        selected_ids = set(self.cleaned_data["acteurs"].values_list("id", flat=True))

        # Récupère les identifiants des acteurs déjà associés au film
        # dans la table Casting.
        existing_ids = set(film.castings.values_list("acteur_id", flat=True))

        # Supprime les castings existants dont l'acteur n'est plus sélectionné.
        #
        # Exemple :
        # si un acteur était associé au film mais que l'administrateur le retire
        # dans le formulaire, son Casting est supprimé ici.
        film.castings.exclude(acteur_id__in=selected_ids).delete()

        # Crée les nouveaux castings manquants.
        #
        # selected_ids - existing_ids représente uniquement les acteurs sélectionnés
        # qui ne sont pas encore associés au film.
        #
        # bulk_create permet d'insérer plusieurs lignes Casting en une seule opération,
        # ce qui est plus efficace que plusieurs create() successifs.
        Casting.objects.bulk_create(
            [
                Casting(film=film, acteur_id=acteur_id)
                for acteur_id in selected_ids - existing_ids
            ]
        )


class GenreForm(DashboardModelForm):
    # Formulaire utilisé dans le dashboard pour créer ou modifier un genre.
    #
    # Il hérite de DashboardModelForm afin de profiter automatiquement
    # de la mise en forme commune des champs.
    class Meta:
        # Modèle associé au formulaire.
        model = Genre

        # Seul le nom du genre est modifiable depuis ce formulaire.
        fields = ("nom",)


class ActeurForm(DashboardModelForm):
    # Formulaire utilisé dans le dashboard pour créer ou modifier un acteur.
    #
    # Comme GenreForm, il reste volontairement simple :
    # l'acteur ne possède ici qu'un champ principal à éditer.
    class Meta:
        # Modèle associé au formulaire.
        model = Acteur

        # Seul le nom de l'acteur est modifiable depuis ce formulaire.
        fields = ("nom",)