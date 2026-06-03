from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, TemplateView

from .forms import CommentForm, ReviewForm
from .models import Commentaire, Critique, Film, Genre


def _critique_queryset():
    return (
        Critique.objects.select_related("utilisateur")
        .prefetch_related(
            Prefetch(
                "commentaires",
                queryset=Commentaire.objects.select_related("utilisateur"),
            )
        )
    )


def _film_detail_queryset():
    return Film.objects.select_related("genre").prefetch_related(
        "acteurs",
        Prefetch("critiques", queryset=_critique_queryset()),
    )


def _films_mieux_notes(limit):
    return (
        Film.objects.select_related("genre")
        .filter(note_moyenne__isnull=False, nombre_critiques__gt=0)
        .order_by("-note_moyenne", "-nombre_critiques", "titre")[:limit]
    )


def _films_populaires(limit):
    return (
        Film.objects.select_related("genre")
        .filter(nombre_critiques__gt=0)
        .order_by("-nombre_critiques", "-note_moyenne", "titre")[:limit]
    )


def _prepare_comment_forms(critiques, user, bound_form=None, target_id=None):
    if not user.is_authenticated:
        return

    for critique in critiques:
        if critique.pk == target_id:
            critique.comment_form = bound_form
        else:
            critique.comment_form = CommentForm(auto_id=f"id_%s_{critique.pk}")


def _detail_url(film_id, critique_id=None):
    url = reverse("movies:film_detail", args=[film_id])
    if critique_id:
        return f"{url}#critique-{critique_id}"
    return url


def _user_review_from_critiques(critiques, user):
    if not user.is_authenticated:
        return None
    return next(
        (
            critique
            for critique in critiques
            if critique.utilisateur_id == user.id
        ),
        None,
    )


def _review_form_context(film, form, form_title, submit_label, critique=None):
    return {
        "film": film,
        "form": form,
        "critique": critique,
        "form_title": form_title,
        "submit_label": submit_label,
    }


class HomeView(TemplateView):
    """Page d'accueil avec films populaires et films les mieux notés."""

    template_name = "movies/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "films_populaires": _films_populaires(4),
            "films_mieux_notes": _films_mieux_notes(4),
            "nombre_films": Film.objects.count(),
            "nombre_critiques": Critique.objects.count(),
        })
        return context


class MovieListView(TemplateView):
    """Catalogue de films avec filtres par genre, année et note minimale."""

    template_name = "movies/movie_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        films = Film.objects.select_related("genre").all()
        genres = Genre.objects.all()
        annees = [date.year for date in Film.objects.dates("date_sortie", "year", order="DESC")]
        genre_ids = set(genres.values_list("id", flat=True))
        annees_valides = set(annees)
        selected_genre = self.request.GET.get("genre", "").strip()
        selected_annee = self.request.GET.get("annee", "").strip()
        selected_note_min = self.request.GET.get("note_min", "").strip()

        if selected_genre.isdigit() and int(selected_genre) in genre_ids:
            films = films.filter(genre_id=int(selected_genre))
        else:
            selected_genre = ""

        if selected_annee.isdigit() and int(selected_annee) in annees_valides:
            films = films.filter(date_sortie__year=int(selected_annee))
        else:
            selected_annee = ""

        if selected_note_min:
            try:
                note_valeur = Decimal(selected_note_min)
            except (InvalidOperation, ValueError):
                note_valeur = None

            if note_valeur is not None and note_valeur.is_finite() and Decimal("0") <= note_valeur <= Decimal("5"):
                films = films.filter(note_moyenne__gte=note_valeur)
            else:
                selected_note_min = ""

        context.update({
            "films": films,
            "genres": genres,
            "annees": annees,
            "nombre_films": films.count(),
            "selected_genre": selected_genre,
            "selected_annee": selected_annee,
            "selected_note_min": selected_note_min,
        })
        return context


class FilmDetailView(DetailView):

    """Page de détail minimale d'un film, accessible depuis le catalogue."""

    """Affiche un film, ses critiques et les commentaires associés."""

    model = Film
    template_name = "movies/movie_detail.html"


    def get_queryset(self):
        return _film_detail_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        critiques = list(self.object.critiques.all())
        _prepare_comment_forms(critiques, self.request.user)
        context["critiques"] = critiques
        context["user_review"] = _user_review_from_critiques(
            critiques,
            self.request.user,
        )
        return context


@login_required
def review_create(request, film_id):
    """Publie une critique unique pour le film visé."""

    film = get_object_or_404(
        Film.objects.select_related("genre").prefetch_related("acteurs"),
        pk=film_id,
    )
    existing_review = Critique.objects.filter(
        film=film,
        utilisateur=request.user,
    ).first()

    if existing_review:
        messages.info(
            request,
            "Vous avez déjà publié une critique pour ce film.",
        )
        return redirect(_detail_url(film.pk, existing_review.pk))

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            critique = form.save(commit=False)
            critique.film = film
            critique.utilisateur = request.user
            critique.save()
            messages.success(request, "Votre critique a été publiée.")
            return redirect(_detail_url(film.pk, critique.pk))
    else:
        form = ReviewForm()

    return render(
        request,
        "movies/review_form.html",
        _review_form_context(
            film,
            form,
            "Publier une critique",
            "Publier ma critique",
        ),
    )


@login_required
def review_update(request, critique_id):
    """Modifie une critique appartenant à l'utilisateur connecté."""

    critique = get_object_or_404(
        Critique.objects.select_related("film__genre", "utilisateur")
        .prefetch_related("film__acteurs"),
        pk=critique_id,
        utilisateur=request.user,
    )
    film = critique.film

    if request.method == "POST":
        form = ReviewForm(request.POST, instance=critique)
        if form.is_valid():
            critique = form.save()
            messages.success(request, "Votre critique a été mise à jour.")
            return redirect(_detail_url(film.pk, critique.pk))
    else:
        form = ReviewForm(instance=critique)

    return render(
        request,
        "movies/review_form.html",
        _review_form_context(
            film,
            form,
            "Modifier ma critique",
            "Enregistrer les modifications",
            critique,
        ),
    )


@login_required
def review_delete(request, critique_id):
    """Confirme puis supprime une critique appartenant à l'utilisateur."""

    critique = get_object_or_404(
        Critique.objects.select_related("film__genre", "utilisateur")
        .prefetch_related("film__acteurs"),
        pk=critique_id,
        utilisateur=request.user,
    )
    film = critique.film

    if request.method == "POST":
        critique.delete()
        messages.success(request, "Votre critique a été supprimée.")
        return redirect(_detail_url(film.pk))

    return render(
        request,
        "movies/review_confirm_delete.html",
        {
            "film": film,
            "critique": critique,
        },
    )


@login_required
@require_POST
def ajouter_commentaire(request, critique_id):
    """Publie un commentaire sous la critique visée par l'URL uniquement."""

    critique = get_object_or_404(
        Critique.objects.select_related("film"),
        pk=critique_id,
    )
    form = CommentForm(request.POST, auto_id=f"id_%s_{critique.pk}")

    if form.is_valid():
        commentaire = form.save(commit=False)
        commentaire.critique = critique
        commentaire.utilisateur = request.user
        commentaire.save()
        messages.success(request, "Votre commentaire a été publié.")
        detail_url = reverse("movies:film_detail", args=[critique.film_id])
        return redirect(f"{detail_url}#critique-{critique.pk}")

    film = get_object_or_404(_film_detail_queryset(), pk=critique.film_id)
    critiques = list(film.critiques.all())
    _prepare_comment_forms(critiques, request.user, form, critique.pk)
    return render(
        request,
        "movies/movie_detail.html",
        {
            "film": film,
            "critiques": critiques,
            "user_review": _user_review_from_critiques(critiques, request.user),
        },
    )


class RankingView(TemplateView):
    """
    Affiche deux classements des films :
    1. Films les mieux notés (par note moyenne décroissante)
    2. Films les plus populaires (par nombre de critiques décroissant)
    """

    template_name = "movies/ranking.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "films_mieux_notes": _films_mieux_notes(20),
            "films_populaires": _films_populaires(20),
        })
        return context
