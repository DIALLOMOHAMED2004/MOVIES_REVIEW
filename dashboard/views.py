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
    # Mixin utilitaire utilisé par les vues du dashboard.
    #
    # Son rôle est d'ajouter automatiquement une variable "active_section"
    # au contexte envoyé aux templates.
    #
    # Cette variable peut ensuite être utilisée dans les templates du dashboard
    # pour mettre en évidence le menu actif :
    # - home ;
    # - films ;
    # - genres ;
    # - acteurs ;
    # - critiques ;
    # - commentaires ;
    # - utilisateurs.
    #
    # L'avantage de ce mixin est de centraliser cette logique au lieu de répéter
    # le même code dans chaque vue.
    active_section = ""

    def get_context_data(self, **kwargs):
        # Récupère d'abord le contexte standard de la vue parente.
        #
        # Selon la vue utilisée, ce contexte peut déjà contenir :
        # - une liste d'objets pour une ListView ;
        # - un formulaire pour une CreateView ou UpdateView ;
        # - un objet à supprimer pour une DeleteView ;
        # - d'autres variables propres à Django.
        context = super().get_context_data(**kwargs)

        # Ajoute la section active au contexte.
        #
        # Chaque classe fille définit sa propre valeur de active_section.
        # Exemple :
        # FilmListView définit active_section = "films".
        context["active_section"] = self.active_section

        # Retourne le contexte enrichi au template.
        return context


class DashboardHomeView(StaffRequiredMixin, DashboardContextMixin, TemplateView):
    # Vue d'accueil du dashboard administrateur personnalisé.
    #
    # StaffRequiredMixin protège l'accès :
    # seuls les utilisateurs staff ou superusers peuvent accéder à cette page.
    #
    # DashboardContextMixin ajoute active_section au contexte.
    #
    # TemplateView est utilisée car cette page affiche principalement des statistiques
    # et ne correspond pas directement à un formulaire ou à une liste unique.
    template_name = "dashboard/home.html"
    active_section = "home"

    def get_context_data(self, **kwargs):
        # Récupère le modèle utilisateur actif du projet.
        #
        # Cela permet de rester compatible avec un User Django standard
        # ou avec un éventuel modèle utilisateur personnalisé.
        User = get_user_model()

        # Récupère le contexte standard.
        context = super().get_context_data(**kwargs)

        # Ajoute au contexte toutes les statistiques et listes nécessaires
        # à l'affichage de l'accueil du dashboard.
        context.update(
            {
                # Nombre total de films enregistrés.
                "nombre_films": Film.objects.count(),

                # Nombre total de critiques publiées.
                "nombre_critiques": Critique.objects.count(),

                # Nombre total de commentaires publiés.
                "nombre_commentaires": Commentaire.objects.count(),

                # Nombre total d'utilisateurs inscrits.
                "nombre_utilisateurs": User.objects.count(),

                # Liste des 5 dernières critiques publiées.
                #
                # select_related("film", "utilisateur") optimise les requêtes SQL
                # en récupérant directement le film et l'utilisateur liés
                # à chaque critique.
                "dernieres_critiques": Critique.objects.select_related(
                    "film", "utilisateur"
                ).order_by("-date_publication")[:5],

                # Liste des 5 derniers commentaires publiés.
                #
                # Les relations imbriquées sont préchargées pour éviter
                # de multiplier les requêtes dans le template.
                #
                # critique__film récupère le film de la critique.
                # critique__utilisateur récupère l'auteur de la critique.
                # utilisateur récupère l'auteur du commentaire.
                "derniers_commentaires": Commentaire.objects.select_related(
                    "critique__film", "critique__utilisateur", "utilisateur"
                ).order_by("-date_publication")[:5],

                # Top 5 des films les mieux notés.
                #
                # On exclut les films sans note moyenne et ceux sans critique.
                # Le tri se fait par :
                # - meilleure note moyenne ;
                # - plus grand nombre de critiques ;
                # - titre en ordre alphabétique pour stabiliser l'ordre.
                "films_mieux_notes": Film.objects.select_related("genre")
                .filter(note_moyenne__isnull=False, nombre_critiques__gt=0)
                .order_by("-note_moyenne", "-nombre_critiques", "titre")[:5],

                # Top 5 des films les plus populaires.
                #
                # Ici, la popularité est mesurée par le nombre de critiques.
                # On trie ensuite par note moyenne puis par titre.
                "films_populaires": Film.objects.select_related("genre")
                .filter(nombre_critiques__gt=0)
                .order_by("-nombre_critiques", "-note_moyenne", "titre")[:5],
            }
        )

        # Retourne le contexte complet à la page d'accueil du dashboard.
        return context


class FilmListView(StaffRequiredMixin, DashboardContextMixin, ListView):
    # Vue listant les films dans le dashboard.
    #
    # Elle permet à l'administrateur de consulter les films existants
    # et généralement d'accéder aux actions de création, modification ou suppression.
    model = Film
    template_name = "dashboard/film_list.html"
    context_object_name = "films"
    active_section = "films"

    def get_queryset(self):
        # Retourne la liste des films avec optimisation des relations.
        #
        # select_related("genre") récupère le genre du film dans la même requête SQL.
        # prefetch_related("acteurs") récupère efficacement les acteurs liés au film.
        #
        # Cette optimisation est utile si le template affiche le genre et les acteurs
        # de chaque film.
        return Film.objects.select_related("genre").prefetch_related("acteurs")


class FilmCreateView(StaffRequiredMixin, DashboardContextMixin, CreateView):
    # Vue de création d'un film depuis le dashboard.
    #
    # Elle utilise FilmForm, qui contient aussi le champ personnalisé "acteurs"
    # permettant de gérer le casting principal du film.
    model = Film
    form_class = FilmForm
    template_name = "dashboard/form.html"
    success_url = reverse_lazy("dashboard:film_list")
    active_section = "films"

    def get_context_data(self, **kwargs):
        # Récupère le contexte standard de CreateView.
        context = super().get_context_data(**kwargs)

        # Ajoute des informations spécifiques au template générique dashboard/form.html.
        #
        # Ce même template peut être utilisé pour plusieurs formulaires,
        # donc ces variables permettent d'adapter son titre, sa description,
        # son bouton de validation et son lien d'annulation.
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
        # Méthode appelée lorsque le formulaire de création est valide.
        #
        # La création du film et la synchronisation du casting sont placées
        # dans une transaction atomique afin d'éviter un état partiel.
        #
        # Si une erreur survient pendant la synchronisation du casting,
        # la création du film est annulée aussi.
        with transaction.atomic():
            # Enregistre le film via le comportement standard de CreateView.
            #
            # Après cet appel, self.object contient le film créé.
            response = super().form_valid(form)

            # Synchronise les acteurs sélectionnés avec la table Casting.
            form.sync_casting(self.object)

        # Ajoute un message de succès affichable dans l'interface.
        messages.success(self.request, "Le film a été ajouté.")

        # Retourne la réponse standard, généralement une redirection vers success_url.
        return response


class FilmUpdateView(StaffRequiredMixin, DashboardContextMixin, UpdateView):
    # Vue de modification d'un film existant.
    #
    # Elle réutilise FilmForm afin de modifier à la fois les informations du film
    # et les acteurs associés via le casting.
    model = Film
    form_class = FilmForm
    template_name = "dashboard/form.html"
    success_url = reverse_lazy("dashboard:film_list")
    active_section = "films"

    def get_queryset(self):
        # Optimise la récupération du film à modifier en préchargeant ses acteurs.
        #
        # Cela permet notamment de préremplir correctement le champ "acteurs"
        # du formulaire sans multiplier les requêtes.
        return Film.objects.prefetch_related("acteurs")

    def get_context_data(self, **kwargs):
        # Récupère le contexte standard de UpdateView.
        context = super().get_context_data(**kwargs)

        # Ajoute les informations textuelles propres à la page de modification.
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
        # Méthode appelée lorsque le formulaire de modification est valide.
        #
        # Comme pour la création, on utilise une transaction atomique pour garantir
        # que la modification du film et la mise à jour du casting restent cohérentes.
        with transaction.atomic():
            # Enregistre les modifications du film.
            response = super().form_valid(form)

            # Synchronise ensuite les acteurs sélectionnés avec la table Casting.
            form.sync_casting(self.object)

        # Ajoute un message de succès.
        messages.success(self.request, "Le film a été mis à jour.")

        # Retourne la redirection standard.
        return response


class FilmDeleteView(StaffRequiredMixin, DashboardContextMixin, DeleteView):
    # Vue de suppression d'un film.
    #
    # DeleteView affiche généralement une page de confirmation en GET
    # puis supprime réellement l'objet en POST.
    model = Film
    template_name = "dashboard/film_confirm_delete.html"
    success_url = reverse_lazy("dashboard:film_list")
    active_section = "films"

    def get_queryset(self):
        # Optimise la récupération du film à supprimer.
        #
        # select_related("genre") récupère le genre.
        #
        # prefetch_related("acteurs", "critiques__commentaires") précharge :
        # - les acteurs associés au film ;
        # - les critiques du film ;
        # - les commentaires liés aux critiques.
        #
        # Cela peut être utile pour afficher un résumé clair sur la page de confirmation.
        return Film.objects.select_related("genre").prefetch_related(
            "acteurs", "critiques__commentaires"
        )

    def form_valid(self, form):
        # Méthode appelée lorsque la suppression est confirmée en POST.
        response = super().form_valid(form)

        # Ajoute un message confirmant la suppression.
        messages.success(self.request, "Le film a été supprimé.")

        return response


class GenreListView(StaffRequiredMixin, DashboardContextMixin, ListView):
    # Vue listant les genres dans le dashboard.
    model = Genre
    template_name = "dashboard/genre_list.html"
    context_object_name = "genres"
    active_section = "genres"

    def get_queryset(self):
        # Retourne les genres avec une annotation nombre_films.
        #
        # Count("films") compte le nombre de films associés à chaque genre.
        # Cela permet au template d'afficher combien de films utilisent chaque genre.
        return Genre.objects.annotate(nombre_films=Count("films"))


class GenreCreateView(StaffRequiredMixin, DashboardContextMixin, CreateView):
    # Vue de création d'un genre.
    model = Genre
    form_class = GenreForm
    template_name = "dashboard/form.html"
    success_url = reverse_lazy("dashboard:genre_list")
    active_section = "genres"

    def get_context_data(self, **kwargs):
        # Récupère le contexte standard du formulaire.
        context = super().get_context_data(**kwargs)

        # Ajoute les informations d'affichage adaptées à la création d'un genre.
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
        # Ajoute un message de succès avant de déléguer l'enregistrement
        # au comportement standard de CreateView.
        messages.success(self.request, "Le genre a été ajouté.")

        return super().form_valid(form)


class GenreUpdateView(StaffRequiredMixin, DashboardContextMixin, UpdateView):
    # Vue de modification d'un genre existant.
    model = Genre
    form_class = GenreForm
    template_name = "dashboard/form.html"
    success_url = reverse_lazy("dashboard:genre_list")
    active_section = "genres"

    def get_context_data(self, **kwargs):
        # Récupère le contexte standard.
        context = super().get_context_data(**kwargs)

        # Ajoute les textes spécifiques à la modification d'un genre.
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
        # Ajoute un message de succès avant la redirection standard.
        messages.success(self.request, "Le genre a été mis à jour.")

        return super().form_valid(form)


class GenreDeleteView(StaffRequiredMixin, DashboardContextMixin, DeleteView):
    # Vue de suppression d'un genre.
    #
    # Un genre peut être protégé contre la suppression s'il est encore utilisé
    # par un ou plusieurs films.
    model = Genre
    template_name = "dashboard/genre_confirm_delete.html"
    success_url = reverse_lazy("dashboard:genre_list")
    active_section = "genres"

    def post(self, request, *args, **kwargs):
        # Gère explicitement la requête POST de suppression.
        #
        # self.object est défini ici afin que DeleteView sache quel objet supprimer.
        self.object = self.get_object()

        try:
            # Tente d'exécuter la suppression standard.
            return super().post(request, *args, **kwargs)

        except ProtectedError:
            # ProtectedError est levée si la base de données ou les relations Django
            # empêchent la suppression car le genre est encore référencé.
            messages.error(
                request,
                "Ce genre est encore utilisé par un ou plusieurs films.",
            )

            # Redirige vers la liste des genres sans supprimer l'objet.
            return redirect(self.success_url)

    def form_valid(self, form):
        # Méthode appelée lorsque la suppression est autorisée et confirmée.
        response = super().form_valid(form)

        # Ajoute un message de succès après suppression.
        messages.success(self.request, "Le genre a été supprimé.")

        return response


class ActeurListView(StaffRequiredMixin, DashboardContextMixin, ListView):
    # Vue listant les acteurs dans le dashboard.
    model = Acteur
    template_name = "dashboard/acteur_list.html"
    context_object_name = "acteurs"
    active_section = "acteurs"

    def get_queryset(self):
        # Retourne les acteurs avec une annotation nombre_castings.
        #
        # Count("castings") compte le nombre de relations Casting associées
        # à chaque acteur.
        #
        # Cela permet de savoir rapidement si un acteur est utilisé dans des films.
        return Acteur.objects.annotate(nombre_castings=Count("castings"))


class ActeurCreateView(StaffRequiredMixin, DashboardContextMixin, CreateView):
    # Vue de création d'un acteur.
    model = Acteur
    form_class = ActeurForm
    template_name = "dashboard/form.html"
    success_url = reverse_lazy("dashboard:acteur_list")
    active_section = "acteurs"

    def get_context_data(self, **kwargs):
        # Récupère le contexte standard.
        context = super().get_context_data(**kwargs)

        # Ajoute les textes spécifiques au formulaire de création d'un acteur.
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
        # Ajoute un message de succès lors de la création d'un acteur.
        messages.success(self.request, "L'acteur a été ajouté.")

        return super().form_valid(form)


class ActeurUpdateView(StaffRequiredMixin, DashboardContextMixin, UpdateView):
    # Vue de modification d'un acteur.
    model = Acteur
    form_class = ActeurForm
    template_name = "dashboard/form.html"
    success_url = reverse_lazy("dashboard:acteur_list")
    active_section = "acteurs"

    def get_context_data(self, **kwargs):
        # Récupère le contexte standard.
        context = super().get_context_data(**kwargs)

        # Ajoute les textes spécifiques au formulaire de modification d'un acteur.
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
        # Ajoute un message de succès après modification.
        messages.success(self.request, "L'acteur a été mis à jour.")

        return super().form_valid(form)


class ActeurDeleteView(StaffRequiredMixin, DashboardContextMixin, DeleteView):
    # Vue de suppression d'un acteur.
    #
    # La suppression est bloquée manuellement si l'acteur est encore présent
    # dans au moins un casting.
    model = Acteur
    template_name = "dashboard/acteur_confirm_delete.html"
    success_url = reverse_lazy("dashboard:acteur_list")
    active_section = "acteurs"

    def get_queryset(self):
        # Retourne les acteurs avec le nombre de castings associés.
        #
        # Cette information peut être utilisée dans la page de confirmation
        # ou dans la logique d'affichage.
        return Acteur.objects.annotate(nombre_castings=Count("castings"))

    def post(self, request, *args, **kwargs):
        # Gère la requête POST de suppression.
        #
        # On récupère d'abord l'objet concerné.
        self.object = self.get_object()

        # Si l'acteur possède encore des castings,
        # sa suppression est refusée.
        #
        # Cette protection évite de supprimer un acteur encore associé
        # à un ou plusieurs films.
        if self.object.castings.exists():
            messages.error(
                request,
                "Cet acteur est encore associé à un ou plusieurs films.",
            )

            # Redirige vers la liste des acteurs sans supprimer l'acteur.
            return redirect(self.success_url)

        # Si l'acteur n'est lié à aucun casting,
        # on laisse DeleteView effectuer la suppression standard.
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        # Méthode appelée lorsque la suppression est autorisée.
        response = super().form_valid(form)

        # Ajoute un message de succès après suppression.
        messages.success(self.request, "L'acteur a été supprimé.")

        return response


class CritiqueListView(StaffRequiredMixin, DashboardContextMixin, ListView):
    # Vue listant les critiques dans le dashboard.
    #
    # Elle inclut aussi une logique de filtrage par :
    # - film ;
    # - auteur ;
    # - note.
    model = Critique
    template_name = "dashboard/critique_list.html"
    context_object_name = "critiques"
    active_section = "critiques"

    def get_queryset(self):
        # QuerySet de base des critiques.
        #
        # select_related("film", "utilisateur") évite des requêtes supplémentaires
        # lorsque le template affiche le film ou l'auteur de chaque critique.
        queryset = Critique.objects.select_related("film", "utilisateur")

        # Récupère les filtres envoyés en GET depuis l'URL.
        #
        # Exemple :
        # /dashboard/critiques/?film=1&auteur=2&note=4
        #
        # strip() supprime les espaces accidentels.
        film = self.request.GET.get("film", "").strip()
        auteur = self.request.GET.get("auteur", "").strip()
        note = self.request.GET.get("note", "").strip()

        # Filtre par film uniquement si la valeur reçue est numérique.
        #
        # Cela évite les erreurs si l'utilisateur modifie l'URL manuellement
        # avec une valeur invalide.
        if film.isdigit():
            queryset = queryset.filter(film_id=int(film))

        # Filtre par auteur uniquement si la valeur reçue est numérique.
        if auteur.isdigit():
            queryset = queryset.filter(utilisateur_id=int(auteur))

        # Filtre par note uniquement si :
        # - la valeur est numérique ;
        # - la note est comprise entre 1 et 5.
        #
        # Cela évite d'appliquer des notes invalides comme 0, 9 ou du texte.
        if note.isdigit() and 1 <= int(note) <= 5:
            queryset = queryset.filter(note=int(note))

        # Retourne la liste éventuellement filtrée.
        return queryset

    def get_context_data(self, **kwargs):
        # Récupère le modèle utilisateur actif du projet.
        User = get_user_model()

        # Récupère le contexte standard de ListView.
        context = super().get_context_data(**kwargs)

        # Ajoute les filtres actuellement sélectionnés au contexte.
        #
        # Cela permet au template de conserver les valeurs sélectionnées
        # dans les menus déroulants après soumission du formulaire de filtre.
        context["filtres"] = {
            "film": self.request.GET.get("film", "").strip(),
            "auteur": self.request.GET.get("auteur", "").strip(),
            "note": self.request.GET.get("note", "").strip(),
        }

        # Liste des films proposés dans le filtre.
        #
        # On ne propose que les films ayant au moins une critique,
        # afin d'éviter des options inutiles dans le menu.
        #
        # distinct() évite les doublons lorsqu'un film a plusieurs critiques.
        context["films_filtre"] = (
            Film.objects.filter(critiques__isnull=False).distinct().order_by("titre")
        )

        # Liste des auteurs proposés dans le filtre.
        #
        # On ne propose que les utilisateurs ayant écrit au moins une critique.
        # distinct() évite les doublons.
        context["auteurs_filtre"] = (
            User.objects.filter(critiques__isnull=False)
            .distinct()
            .order_by("username")
        )

        # Retourne le contexte enrichi.
        return context


class CritiqueDeleteView(StaffRequiredMixin, DashboardContextMixin, DeleteView):
    # Vue de suppression d'une critique depuis le dashboard.
    #
    # Le GET affiche une confirmation.
    # Le POST confirme et exécute réellement la suppression.
    model = Critique
    template_name = "dashboard/critique_confirm_delete.html"
    success_url = reverse_lazy("dashboard:critique_list")
    active_section = "critiques"

    def get_queryset(self):
        # Optimise la récupération de la critique à supprimer.
        #
        # Le template de confirmation peut afficher le film concerné
        # et l'utilisateur auteur de la critique.
        return Critique.objects.select_related("film", "utilisateur")

    def form_valid(self, form):
        # Méthode appelée quand la suppression est confirmée.
        response = super().form_valid(form)

        # Ajoute un message de succès.
        messages.success(self.request, "La critique a été supprimée.")

        return response


class CommentaireListView(StaffRequiredMixin, DashboardContextMixin, ListView):
    # Vue listant les commentaires dans le dashboard.
    model = Commentaire
    template_name = "dashboard/commentaire_list.html"
    context_object_name = "commentaires"
    active_section = "commentaires"

    def get_queryset(self):
        # Retourne les commentaires avec leurs relations principales préchargées.
        #
        # utilisateur : auteur du commentaire.
        # critique__film : film concerné par la critique commentée.
        # critique__utilisateur : auteur de la critique commentée.
        #
        # order_by("-date_publication") affiche les commentaires récents en premier.
        return Commentaire.objects.select_related(
            "utilisateur", "critique__film", "critique__utilisateur"
        ).order_by("-date_publication")


class CommentaireDeleteView(StaffRequiredMixin, DashboardContextMixin, DeleteView):
    # Vue de suppression d'un commentaire depuis le dashboard.
    model = Commentaire
    template_name = "dashboard/commentaire_confirm_delete.html"
    success_url = reverse_lazy("dashboard:commentaire_list")
    active_section = "commentaires"

    def get_queryset(self):
        # Optimise la récupération du commentaire à supprimer
        # et des informations utiles pour la page de confirmation.
        return Commentaire.objects.select_related(
            "utilisateur", "critique__film", "critique__utilisateur"
        )

    def form_valid(self, form):
        # Méthode appelée lorsque la suppression est confirmée.
        response = super().form_valid(form)

        # Ajoute un message de succès.
        messages.success(self.request, "Le commentaire a été supprimé.")

        return response


class UserListView(StaffRequiredMixin, DashboardContextMixin, ListView):
    # Vue listant les utilisateurs inscrits dans le dashboard.
    #
    # Elle n'utilise pas directement model = User, car le modèle utilisateur
    # est récupéré dynamiquement avec get_user_model().
    #
    # Cette approche est plus robuste si le projet utilise un modèle utilisateur
    # personnalisé.
    template_name = "dashboard/user_list.html"
    context_object_name = "utilisateurs"
    active_section = "utilisateurs"

    def get_queryset(self):
        # Récupère le modèle utilisateur actif.
        User = get_user_model()

        # Retourne les utilisateurs avec deux annotations :
        # - nombre_critiques ;
        # - nombre_commentaires.
        #
        # distinct=True évite les comptages incorrects lorsque plusieurs jointures
        # sont impliquées dans la même requête.
        #
        # order_by("username") classe les utilisateurs par nom d'utilisateur.
        return User.objects.annotate(
            nombre_critiques=Count("critiques", distinct=True),
            nombre_commentaires=Count("commentaires", distinct=True),
        ).order_by("username")