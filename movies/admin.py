from django.contrib import admin

from .models import Genre, Acteur, Film, Casting, Critique, Commentaire


class CastingInline(admin.TabularInline):
    # Inline Django Admin permettant de gérer les castings directement
    # depuis la page d'administration d'un film.
    #
    # TabularInline affiche les relations sous forme de tableau compact.
    # Cela permet, lorsqu'on édite un Film dans l'admin Django,
    # d'ajouter ou modifier rapidement les acteurs associés à ce film.
    model = Casting

    # Nombre de lignes vides supplémentaires affichées dans l'interface admin.
    #
    # Ici, extra = 1 signifie qu'une ligne vide sera disponible par défaut
    # pour ajouter un nouveau casting.
    extra = 1


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    # Configuration de l'interface Django Admin pour le modèle Genre.
    #
    # Le décorateur @admin.register(Genre) enregistre automatiquement
    # le modèle Genre avec cette classe d'administration.

    # Champs affichés dans la liste des genres.
    list_display = ("nom",)

    # Champs utilisés par la barre de recherche de l'admin.
    #
    # Ici, on peut rechercher un genre par son nom.
    search_fields = ("nom",)


@admin.register(Acteur)
class ActeurAdmin(admin.ModelAdmin):
    # Configuration de l'interface Django Admin pour le modèle Acteur.

    # Champs affichés dans la liste des acteurs.
    list_display = ("nom",)

    # Permet de rechercher un acteur par son nom.
    search_fields = ("nom",)


@admin.register(Casting)
class CastingAdmin(admin.ModelAdmin):
    # Configuration de l'interface Django Admin pour le modèle Casting.
    #
    # Casting représente la relation entre un film et un acteur.
    # Cette table permet donc de savoir quels acteurs jouent dans quels films.

    # Colonnes affichées dans la liste des castings.
    list_display = ("film", "acteur")

    # Optimise les requêtes SQL dans l'admin.
    #
    # Comme film et acteur sont des ForeignKey,
    # list_select_related permet de récupérer les objets liés dans la même requête.
    # Cela évite des requêtes supplémentaires pour chaque ligne affichée.
    list_select_related = ("film", "acteur")

    # Champs sur lesquels la recherche admin peut être effectuée.
    #
    # film__titre permet de chercher par titre de film.
    # acteur__nom permet de chercher par nom d'acteur.
    search_fields = ("film__titre", "acteur__nom")


@admin.register(Film)
class FilmAdmin(admin.ModelAdmin):
    # Configuration de l'interface Django Admin pour le modèle Film.

    # Colonnes affichées dans la liste des films.
    #
    # Cela donne une vue rapide des informations principales :
    # titre, genre, date de sortie, durée, note moyenne et nombre de critiques.
    list_display = (
        "titre",
        "genre",
        "date_sortie",
        "duree_minutes",
        "note_moyenne",
        "nombre_critiques",
    )

    # Filtres latéraux disponibles dans l'admin.
    #
    # Ils permettent de filtrer rapidement les films par genre ou date de sortie.
    list_filter = ("genre", "date_sortie")

    # Optimise l'affichage de la liste en récupérant le genre
    # dans la même requête que les films.
    list_select_related = ("genre",)

    # Champs utilisés par la recherche admin.
    #
    # On peut rechercher un film par son titre ou par son synopsis.
    search_fields = ("titre", "synopsis")

    # Champs affichés en lecture seule dans le formulaire admin.
    #
    # note_moyenne et nombre_critiques sont des valeurs calculées automatiquement
    # à partir des critiques.
    #
    # Elles ne doivent donc pas être modifiées manuellement par l'administrateur.
    readonly_fields = ("note_moyenne", "nombre_critiques")

    # Ajoute l'inline CastingInline dans la page d'édition d'un film.
    #
    # Cela permet de gérer les acteurs associés au film directement
    # depuis le formulaire admin du film.
    inlines = [CastingInline]


@admin.register(Critique)
class CritiqueAdmin(admin.ModelAdmin):
    # Configuration de l'interface Django Admin pour le modèle Critique.
    #
    # Une critique est liée à :
    # - un film ;
    # - un utilisateur ;
    # - une note ;
    # - un titre ;
    # - un texte ;
    # - des dates de publication et modification.

    # Colonnes affichées dans la liste des critiques.
    list_display = (
        "titre",
        "film",
        "utilisateur",
        "note",
        "date_publication",
        "date_modification",
    )

    # Filtres latéraux disponibles.
    #
    # Permet de filtrer les critiques par note ou par date de publication.
    list_filter = ("note", "date_publication")

    # Optimise les requêtes dans la liste des critiques.
    #
    # film et utilisateur sont des relations ForeignKey.
    # Les charger en avance évite une requête supplémentaire par critique affichée.
    list_select_related = ("film", "utilisateur")

    # Champs utilisés par la recherche.
    #
    # titre et texte recherchent dans le contenu de la critique.
    # film__titre permet de chercher par titre de film.
    # utilisateur__username permet de chercher par nom d'utilisateur.
    search_fields = ("titre", "texte", "film__titre", "utilisateur__username")

    # Dates affichées en lecture seule.
    #
    # Ces champs sont gérés automatiquement par le modèle
    # et ne doivent pas être modifiés manuellement.
    readonly_fields = ("date_publication", "date_modification")

    def delete_queryset(self, request, queryset):
        # Méthode appelée lorsque l'administrateur supprime plusieurs critiques
        # en une seule action depuis la liste Django Admin.
        #
        # Point important :
        # lorsqu'on utilise queryset.delete(), Django supprime les objets en masse.
        # Dans ce cas, la méthode delete() individuelle du modèle Critique
        # peut être contournée selon la logique du projet.
        #
        # Or, dans ce projet, la suppression d'une critique doit mettre à jour
        # les statistiques du film associé :
        # - nombre_critiques ;
        # - note_moyenne.
        #
        # Cette méthode surcharge donc le comportement par défaut pour recalculer
        # explicitement les statistiques des films concernés après suppression.

        # Récupère les identifiants des films liés aux critiques qui vont être supprimées.
        #
        # set(...) évite les doublons si plusieurs critiques appartiennent au même film.
        film_ids = set(queryset.values_list("film_id", flat=True))

        # Exécute la suppression standard de Django Admin.
        super().delete_queryset(request, queryset)

        # QuerySet.delete() contourne Critique.delete(); les statistiques doivent
        # donc être recalculées explicitement pour les films encore présents.
        for film in Film.objects.filter(pk__in=film_ids):
            # Recalcule les statistiques du film après suppression des critiques.
            film.mettre_a_jour_statistiques()


@admin.register(Commentaire)
class CommentaireAdmin(admin.ModelAdmin):
    # Configuration de l'interface Django Admin pour le modèle Commentaire.
    #
    # Un commentaire est lié à :
    # - un utilisateur ;
    # - une critique ;
    # - indirectement un film via la critique ;
    # - une date de publication.

    # Colonnes affichées dans la liste des commentaires.
    #
    # "extrait" et "film" sont des méthodes personnalisées définies plus bas.
    list_display = (
        "extrait",
        "utilisateur",
        "film",
        "critique",
        "date_publication",
    )

    # Filtre latéral par date de publication.
    list_filter = ("date_publication",)

    # Optimise les requêtes SQL pour l'affichage des commentaires.
    #
    # utilisateur : auteur du commentaire.
    # critique__film : film concerné par la critique commentée.
    # critique__utilisateur : auteur de la critique commentée.
    list_select_related = ("utilisateur", "critique__film", "critique__utilisateur")

    # Champs utilisés par la recherche admin.
    #
    # texte : contenu du commentaire.
    # utilisateur__username : nom de l'auteur du commentaire.
    # critique__titre : titre de la critique commentée.
    search_fields = ("texte", "utilisateur__username", "critique__titre")

    # La date de publication est gérée automatiquement,
    # donc elle est affichée en lecture seule.
    readonly_fields = ("date_publication",)

    @admin.display(description="Extrait du commentaire")
    def extrait(self, obj):
        # Méthode utilisée comme colonne personnalisée dans list_display.
        #
        # Elle affiche un aperçu court du commentaire pour éviter d'avoir
        # des textes trop longs dans la liste admin.
        #
        # Si le commentaire dépasse 75 caractères :
        # - on affiche les 75 premiers caractères ;
        # - on ajoute "...".
        #
        # Sinon, on affiche le texte complet.
        return f"{obj.texte[:75]}..." if len(obj.texte) > 75 else obj.texte

    @admin.display(description="Film", ordering="critique__film__titre")
    def film(self, obj):
        # Méthode utilisée comme colonne personnalisée dans list_display.
        #
        # Un commentaire n'est pas directement lié à un film.
        # Il est lié à une critique, et cette critique est liée à un film.
        #
        # Cette méthode permet donc d'afficher directement le film concerné
        # dans la liste des commentaires.
        #
        # ordering="critique__film__titre" permet aussi de trier cette colonne
        # par titre de film dans l'interface admin.
        return obj.critique.film