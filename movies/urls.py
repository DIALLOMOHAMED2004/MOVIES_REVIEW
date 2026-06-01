from django.urls import path

from .views import (
    FilmDetailView,
    HomeView,
    MovieListView,
    RankingView,
    ajouter_commentaire,
)


app_name = "movies"

urlpatterns = [
    path("", HomeView.as_view(), name="accueil"),
    path("films/", MovieListView.as_view(), name="films"),
    path("films/<int:pk>/", FilmDetailView.as_view(), name="film_detail"),
    path(
        "critiques/<int:critique_id>/commentaires/ajouter/",
        ajouter_commentaire,
        name="ajouter_commentaire",
    ),
    path("classement/", RankingView.as_view(), name="classement"),
]
