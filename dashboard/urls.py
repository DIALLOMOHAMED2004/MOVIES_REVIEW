from django.urls import path

from . import views


app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardHomeView.as_view(), name="home"),
    path("films/", views.FilmListView.as_view(), name="film_list"),
    path("films/ajouter/", views.FilmCreateView.as_view(), name="film_create"),
    path("films/<int:pk>/modifier/", views.FilmUpdateView.as_view(), name="film_update"),
    path("films/<int:pk>/supprimer/", views.FilmDeleteView.as_view(), name="film_delete"),
    path("genres/", views.GenreListView.as_view(), name="genre_list"),
    path("genres/ajouter/", views.GenreCreateView.as_view(), name="genre_create"),
    path("genres/<int:pk>/modifier/", views.GenreUpdateView.as_view(), name="genre_update"),
    path("genres/<int:pk>/supprimer/", views.GenreDeleteView.as_view(), name="genre_delete"),
    path("acteurs/", views.ActeurListView.as_view(), name="acteur_list"),
    path("acteurs/ajouter/", views.ActeurCreateView.as_view(), name="acteur_create"),
    path("acteurs/<int:pk>/modifier/", views.ActeurUpdateView.as_view(), name="acteur_update"),
    path("acteurs/<int:pk>/supprimer/", views.ActeurDeleteView.as_view(), name="acteur_delete"),
    path("critiques/", views.CritiqueListView.as_view(), name="critique_list"),
    path("critiques/<int:pk>/supprimer/", views.CritiqueDeleteView.as_view(), name="critique_delete"),
    path("commentaires/", views.CommentaireListView.as_view(), name="commentaire_list"),
    path("commentaires/<int:pk>/supprimer/", views.CommentaireDeleteView.as_view(), name="commentaire_delete"),
    path("utilisateurs/", views.UserListView.as_view(), name="user_list"),
]
