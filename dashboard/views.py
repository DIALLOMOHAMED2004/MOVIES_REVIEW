from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from movies.models import Acteur, Commentaire, Critique, Film, Genre

from .forms import ActeurForm, FilmForm, GenreForm
from .mixins import StaffRequiredMixin


class DashboardContextMixin:
    active_section = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_section"] = self.active_section
        return context


class DashboardHomeView(StaffRequiredMixin, DashboardContextMixin, TemplateView):
    template_name = "dashboard/home.html"
    active_section = "home"

    def get_context_data(self, **kwargs):
        User = get_user_model()
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "nombre_films": Film.objects.count(),
                "nombre_critiques": Critique.objects.count(),
                "nombre_commentaires": Commentaire.objects.count(),
                "nombre_utilisateurs": User.objects.count(),
                "dernieres_critiques": Critique.objects.select_related(
                    "film", "utilisateur"
                ).order_by("-date_publication")[:5],
                "derniers_commentaires": Commentaire.objects.select_related(
                    "critique__film", "critique__utilisateur", "utilisateur"
                ).order_by("-date_publication")[:5],
                "films_mieux_notes": Film.objects.select_related("genre")
                .filter(note_moyenne__isnull=False, nombre_critiques__gt=0)
                .order_by("-note_moyenne", "-nombre_critiques", "titre")[:5],
                "films_populaires": Film.objects.select_related("genre")
                .filter(nombre_critiques__gt=0)
                .order_by("-nombre_critiques", "-note_moyenne", "titre")[:5],
            }
        )
        return context


class FilmListView(StaffRequiredMixin, DashboardContextMixin, ListView):
    model = Film
    template_name = "dashboard/film_list.html"
    context_object_name = "films"
    active_section = "films"

    def get_queryset(self):
        return Film.objects.select_related("genre").prefetch_related("acteurs")


class FilmCreateView(StaffRequiredMixin, DashboardContextMixin, CreateView):
    model = Film
    form_class = FilmForm
    template_name = "dashboard/form.html"
    success_url = reverse_lazy("dashboard:film_list")
    active_section = "films"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Ajouter un film",
                "form_description": "Renseignez les informations du film et son casting principal.",
                "submit_label": "Créer le film",
                "cancel_url": reverse_lazy("dashboard:film_list"),
            }
        )
        return context

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            form.sync_casting(self.object)
        messages.success(self.request, "Le film a été ajouté.")
        return response


class FilmUpdateView(StaffRequiredMixin, DashboardContextMixin, UpdateView):
    model = Film
    form_class = FilmForm
    template_name = "dashboard/form.html"
    success_url = reverse_lazy("dashboard:film_list")
    active_section = "films"

    def get_queryset(self):
        return Film.objects.prefetch_related("acteurs")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Modifier le film",
                "form_description": "Mettez à jour les informations du film et son casting principal.",
                "submit_label": "Enregistrer",
                "cancel_url": reverse_lazy("dashboard:film_list"),
            }
        )
        return context

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            form.sync_casting(self.object)
        messages.success(self.request, "Le film a été mis à jour.")
        return response


class FilmDeleteView(StaffRequiredMixin, DashboardContextMixin, DeleteView):
    model = Film
    template_name = "dashboard/film_confirm_delete.html"
    success_url = reverse_lazy("dashboard:film_list")
    active_section = "films"

    def get_queryset(self):
        return Film.objects.select_related("genre").prefetch_related(
            "acteurs", "critiques__commentaires"
        )

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Le film a été supprimé.")
        return response


class GenreListView(StaffRequiredMixin, DashboardContextMixin, ListView):
    model = Genre
    template_name = "dashboard/genre_list.html"
    context_object_name = "genres"
    active_section = "genres"

    def get_queryset(self):
        return Genre.objects.annotate(nombre_films=Count("films"))


class GenreCreateView(StaffRequiredMixin, DashboardContextMixin, CreateView):
    model = Genre
    form_class = GenreForm
    template_name = "dashboard/form.html"
    success_url = reverse_lazy("dashboard:genre_list")
    active_section = "genres"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Ajouter un genre",
                "form_description": "Renseignez le nom du genre.",
                "submit_label": "Créer le genre",
                "cancel_url": reverse_lazy("dashboard:genre_list"),
            }
        )
        return context

    def form_valid(self, form):
        messages.success(self.request, "Le genre a été ajouté.")
        return super().form_valid(form)


class GenreUpdateView(StaffRequiredMixin, DashboardContextMixin, UpdateView):
    model = Genre
    form_class = GenreForm
    template_name = "dashboard/form.html"
    success_url = reverse_lazy("dashboard:genre_list")
    active_section = "genres"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Modifier le genre",
                "form_description": "Mettez à jour le nom du genre.",
                "submit_label": "Enregistrer",
                "cancel_url": reverse_lazy("dashboard:genre_list"),
            }
        )
        return context

    def form_valid(self, form):
        messages.success(self.request, "Le genre a été mis à jour.")
        return super().form_valid(form)


class GenreDeleteView(StaffRequiredMixin, DashboardContextMixin, DeleteView):
    model = Genre
    template_name = "dashboard/genre_confirm_delete.html"
    success_url = reverse_lazy("dashboard:genre_list")
    active_section = "genres"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request,
                "Ce genre est encore utilisé par un ou plusieurs films.",
            )
            return redirect(self.success_url)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Le genre a été supprimé.")
        return response


class ActeurListView(StaffRequiredMixin, DashboardContextMixin, ListView):
    model = Acteur
    template_name = "dashboard/acteur_list.html"
    context_object_name = "acteurs"
    active_section = "acteurs"

    def get_queryset(self):
        return Acteur.objects.annotate(nombre_castings=Count("castings"))


class ActeurCreateView(StaffRequiredMixin, DashboardContextMixin, CreateView):
    model = Acteur
    form_class = ActeurForm
    template_name = "dashboard/form.html"
    success_url = reverse_lazy("dashboard:acteur_list")
    active_section = "acteurs"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Ajouter un acteur",
                "form_description": "Renseignez le nom de l'acteur.",
                "submit_label": "Créer l'acteur",
                "cancel_url": reverse_lazy("dashboard:acteur_list"),
            }
        )
        return context

    def form_valid(self, form):
        messages.success(self.request, "L'acteur a été ajouté.")
        return super().form_valid(form)


class ActeurUpdateView(StaffRequiredMixin, DashboardContextMixin, UpdateView):
    model = Acteur
    form_class = ActeurForm
    template_name = "dashboard/form.html"
    success_url = reverse_lazy("dashboard:acteur_list")
    active_section = "acteurs"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Modifier l'acteur",
                "form_description": "Mettez à jour le nom de l'acteur.",
                "submit_label": "Enregistrer",
                "cancel_url": reverse_lazy("dashboard:acteur_list"),
            }
        )
        return context

    def form_valid(self, form):
        messages.success(self.request, "L'acteur a été mis à jour.")
        return super().form_valid(form)


class ActeurDeleteView(StaffRequiredMixin, DashboardContextMixin, DeleteView):
    model = Acteur
    template_name = "dashboard/acteur_confirm_delete.html"
    success_url = reverse_lazy("dashboard:acteur_list")
    active_section = "acteurs"

    def get_queryset(self):
        return Acteur.objects.annotate(nombre_castings=Count("castings"))

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.castings.exists():
            messages.error(
                request,
                "Cet acteur est encore associé à un ou plusieurs films.",
            )
            return redirect(self.success_url)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "L'acteur a été supprimé.")
        return response


class CritiqueListView(StaffRequiredMixin, DashboardContextMixin, ListView):
    model = Critique
    template_name = "dashboard/critique_list.html"
    context_object_name = "critiques"
    active_section = "critiques"

    def get_queryset(self):
        queryset = Critique.objects.select_related("film", "utilisateur")
        film = self.request.GET.get("film", "").strip()
        auteur = self.request.GET.get("auteur", "").strip()
        note = self.request.GET.get("note", "").strip()

        if film.isdigit():
            queryset = queryset.filter(film_id=int(film))
        if auteur.isdigit():
            queryset = queryset.filter(utilisateur_id=int(auteur))
        if note.isdigit() and 1 <= int(note) <= 5:
            queryset = queryset.filter(note=int(note))
        return queryset

    def get_context_data(self, **kwargs):
        User = get_user_model()
        context = super().get_context_data(**kwargs)
        context["filtres"] = {
            "film": self.request.GET.get("film", "").strip(),
            "auteur": self.request.GET.get("auteur", "").strip(),
            "note": self.request.GET.get("note", "").strip(),
        }
        context["films_filtre"] = (
            Film.objects.filter(critiques__isnull=False).distinct().order_by("titre")
        )
        context["auteurs_filtre"] = (
            User.objects.filter(critiques__isnull=False)
            .distinct()
            .order_by("username")
        )
        return context


class CritiqueDeleteView(StaffRequiredMixin, DashboardContextMixin, DeleteView):
    model = Critique
    template_name = "dashboard/critique_confirm_delete.html"
    success_url = reverse_lazy("dashboard:critique_list")
    active_section = "critiques"

    def get_queryset(self):
        return Critique.objects.select_related("film", "utilisateur")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "La critique a été supprimée.")
        return response


class CommentaireListView(StaffRequiredMixin, DashboardContextMixin, ListView):
    model = Commentaire
    template_name = "dashboard/commentaire_list.html"
    context_object_name = "commentaires"
    active_section = "commentaires"

    def get_queryset(self):
        return Commentaire.objects.select_related(
            "utilisateur", "critique__film", "critique__utilisateur"
        ).order_by("-date_publication")


class CommentaireDeleteView(StaffRequiredMixin, DashboardContextMixin, DeleteView):
    model = Commentaire
    template_name = "dashboard/commentaire_confirm_delete.html"
    success_url = reverse_lazy("dashboard:commentaire_list")
    active_section = "commentaires"

    def get_queryset(self):
        return Commentaire.objects.select_related(
            "utilisateur", "critique__film", "critique__utilisateur"
        )

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Le commentaire a été supprimé.")
        return response


class UserListView(StaffRequiredMixin, DashboardContextMixin, ListView):
    template_name = "dashboard/user_list.html"
    context_object_name = "utilisateurs"
    active_section = "utilisateurs"

    def get_queryset(self):
        User = get_user_model()
        return User.objects.annotate(
            nombre_critiques=Count("critiques", distinct=True),
            nombre_commentaires=Count("commentaires", distinct=True),
        ).order_by("username")
