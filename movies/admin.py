from django.contrib import admin

from .models import Genre, Acteur, Film, Casting, Critique, Commentaire


class CastingInline(admin.TabularInline):
    model = Casting
    extra = 1


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("nom",)
    search_fields = ("nom",)


@admin.register(Acteur)
class ActeurAdmin(admin.ModelAdmin):
    list_display = ("nom",)
    search_fields = ("nom",)


@admin.register(Casting)
class CastingAdmin(admin.ModelAdmin):
    list_display = ("film", "acteur")
    list_select_related = ("film", "acteur")
    search_fields = ("film__titre", "acteur__nom")


@admin.register(Film)
class FilmAdmin(admin.ModelAdmin):
    list_display = (
        "titre",
        "genre",
        "date_sortie",
        "duree_minutes",
        "note_moyenne",
        "nombre_critiques",
    )
    list_filter = ("genre", "date_sortie")
    list_select_related = ("genre",)
    search_fields = ("titre", "synopsis")
    readonly_fields = ("note_moyenne", "nombre_critiques")
    inlines = [CastingInline]


@admin.register(Critique)
class CritiqueAdmin(admin.ModelAdmin):
    list_display = (
        "titre",
        "film",
        "utilisateur",
        "note",
        "date_publication",
        "date_modification",
    )
    list_filter = ("note", "date_publication")
    list_select_related = ("film", "utilisateur")
    search_fields = ("titre", "texte", "film__titre", "utilisateur__username")
    readonly_fields = ("date_publication", "date_modification")

    def delete_queryset(self, request, queryset):
        film_ids = set(queryset.values_list("film_id", flat=True))
        super().delete_queryset(request, queryset)

        # QuerySet.delete() contourne Critique.delete(); les statistiques doivent
        # donc être recalculées explicitement pour les films encore présents.
        for film in Film.objects.filter(pk__in=film_ids):
            film.mettre_a_jour_statistiques()


@admin.register(Commentaire)
class CommentaireAdmin(admin.ModelAdmin):
    list_display = (
        "extrait",
        "utilisateur",
        "film",
        "critique",
        "date_publication",
    )
    list_filter = ("date_publication",)
    list_select_related = ("utilisateur", "critique__film", "critique__utilisateur")
    search_fields = ("texte", "utilisateur__username", "critique__titre")
    readonly_fields = ("date_publication",)

    @admin.display(description="Extrait du commentaire")
    def extrait(self, obj):
        return f"{obj.texte[:75]}..." if len(obj.texte) > 75 else obj.texte

    @admin.display(description="Film", ordering="critique__film__titre")
    def film(self, obj):
        return obj.critique.film
