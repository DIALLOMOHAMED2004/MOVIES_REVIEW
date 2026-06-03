from django.urls import path

from .views import (
    FilmDetailView,
    HomeView,
    MovieListView,
    RankingView,
    ajouter_commentaire,
    review_create,
    review_delete,
    review_update,
)


app_name = "movies"

urlpatterns = [
    path("", HomeView.as_view(), name="accueil"),
    path("films/", MovieListView.as_view(), name="films"),
    path("films/<int:pk>/", FilmDetailView.as_view(), name="film_detail"),
    path(
        "films/<int:film_id>/critiques/ajouter/",
        review_create,
        name="review_create",
    ),
    path(
        "critiques/<int:critique_id>/modifier/",
        review_update,
        name="review_update",
    ),
    path(
        "critiques/<int:critique_id>/supprimer/",
        review_delete,
        name="review_delete",
    ),
    path(
        "critiques/<int:critique_id>/commentaires/ajouter/",
        ajouter_commentaire,
        name="ajouter_commentaire",
    ),
    path("classement/", RankingView.as_view(), name="classement"),
]
