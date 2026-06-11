"""
Module de vues de l'application `movies`.

Ce fichier regroupe la logique de présentation principale liée aux films,
aux critiques, aux commentaires, à la page d'accueil, au catalogue et aux
classements.

Rôle global du module
---------------------
Ce module appartient à une application Django de type "Movie Review".
Il sert d'intermédiaire entre :
- les requêtes HTTP reçues par Django ;
- les modèles de données (`Film`, `Critique`, `Commentaire`, `Genre`) ;
- les formulaires (`ReviewForm`, `CommentForm`) ;
- les templates HTML affichés à l'utilisateur.

Les vues présentes ici couvrent notamment :
- l'affichage de la page d'accueil ;
- l'affichage du catalogue des films avec filtres ;
- l'affichage du détail d'un film avec ses critiques et commentaires ;
- la création, modification et suppression d'une critique ;
- l'ajout d'un commentaire sous une critique ;
- l'affichage de classements de films.

Principes importants
--------------------
- Les fonctions préfixées par `_` sont des fonctions utilitaires internes au module.
  Elles ne sont normalement pas destinées à être appelées directement depuis les URL.
- Les requêtes SQL sont optimisées avec `select_related`, `prefetch_related` et
  `Prefetch` afin de limiter les problèmes de type N+1 queries.
- Les associations sensibles, comme l'utilisateur auteur d'une critique ou d'un
  commentaire, ne sont jamais prises depuis les données POST envoyées par le client.
  Elles sont imposées côté serveur à partir de `request.user` et de l'URL.
- Les vues de création, modification, suppression et ajout de commentaire sont
  protégées par `login_required`, car elles nécessitent un utilisateur authentifié.
"""

# Import de la classe `date` du module standard `datetime`.
# Elle est utilisée ici pour extraire proprement l'année des dates de sortie
# récupérées depuis la base de données dans le catalogue.
from datetime import date

# Decimal permet de manipuler les notes minimales avec précision.
# InvalidOperation permet d'intercepter les conversions invalides vers Decimal,
# par exemple lorsqu'un utilisateur envoie une valeur non numérique dans l'URL.
from decimal import Decimal, InvalidOperation

# Framework de messages temporaires de Django.
# Il permet d'afficher à l'utilisateur des confirmations ou informations après
# une action : critique publiée, critique modifiée, commentaire ajouté, etc.
from django.contrib import messages

# Décorateur Django imposant que l'utilisateur soit connecté avant d'accéder
# à une vue fonctionnelle.
from django.contrib.auth.decorators import login_required

# Prefetch permet de personnaliser finement les préchargements de relations.
# Il est particulièrement utile ici pour charger les commentaires avec leurs
# utilisateurs en une requête optimisée.
from django.db.models import Prefetch, Q

# Fonctions de raccourci Django :
# - get_object_or_404 : récupère un objet ou renvoie automatiquement une 404 ;
# - redirect : produit une redirection HTTP ;
# - render : rend un template avec un contexte.
from django.shortcuts import get_object_or_404, redirect, render

# reverse permet de générer une URL à partir de son nom déclaré dans urls.py.
# Cela évite de coder les chemins en dur dans les vues.
from django.urls import reverse

# Décorateur imposant que la vue accepte uniquement les requêtes POST.
# Il est utilisé pour éviter qu'une action d'écriture soit déclenchée par GET.
from django.views.decorators.http import require_POST

# Vues génériques Django :
# - DetailView : vue spécialisée pour afficher le détail d'un objet ;
# - TemplateView : vue simple basée sur un template et un contexte.
from django.views.generic import DetailView, TemplateView

# Formulaires applicatifs :
# - CommentForm : validation et création des commentaires ;
# - ReviewForm : validation et création/modification des critiques.
from .forms import CommentForm, ReviewForm

# Modèles métier utilisés par les vues.
# Ces modèles représentent les films, genres, critiques et commentaires.
from .models import Commentaire, Critique, Film, Genre


# ============================================================================
# Fonctions utilitaires internes
# ============================================================================
#
# Les fonctions suivantes factorisent de la logique commune utilisée par plusieurs
# vues. Elles évitent la duplication de code et centralisent les choix importants,
# notamment les optimisations de requêtes et la construction d'URL.
#
# Le préfixe `_` indique qu'elles sont internes à ce module.


def _critique_queryset():
    """
    Construit le queryset optimisé utilisé pour récupérer les critiques.

    Objectif
    --------
    Cette fonction retourne un queryset de `Critique` qui précharge :
    - l'utilisateur auteur de chaque critique ;
    - les commentaires associés à chaque critique ;
    - l'utilisateur auteur de chaque commentaire.

    Pourquoi cette optimisation ?
    -----------------------------
    Sur une page détail de film, on affiche généralement plusieurs critiques,
    et chaque critique peut avoir plusieurs commentaires. Sans préchargement,
    le template pourrait déclencher une requête SQL supplémentaire pour chaque
    utilisateur, chaque critique ou chaque commentaire affiché.

    `select_related("utilisateur")`
        Utilisé pour une relation de type ForeignKey entre `Critique` et
        l'utilisateur. Django effectue une jointure SQL et récupère l'utilisateur
        dans la même requête.

    `prefetch_related(Prefetch(...))`
        Utilisé pour les commentaires, relation multiple. Django effectue une
        requête séparée optimisée et rattache ensuite les commentaires aux
        critiques correspondantes en mémoire.

    Retour
    ------
    QuerySet[Critique]
        Queryset prêt à être utilisé dans un préchargement ou dans une vue.

    Effets de bord
    --------------
    Aucun accès immédiat à la base tant que le queryset n'est pas évalué.
    """
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
    """
    Construit le queryset optimisé pour la page détail d'un film.

    Objectif
    --------
    Cette fonction centralise la récupération complète d'un film avec les données
    nécessaires à son affichage détaillé :
    - son genre ;
    - ses acteurs ;
    - ses critiques ;
    - les utilisateurs des critiques ;
    - les commentaires associés aux critiques ;
    - les utilisateurs des commentaires.

    Pourquoi cette fonction existe ?
    --------------------------------
    Plusieurs vues ont besoin de reconstruire le contexte complet d'une page
    détail, notamment :
    - `FilmDetailView`, pour l'affichage normal ;
    - `ajouter_commentaire`, lorsqu'un formulaire de commentaire invalide doit
      réafficher la page avec les erreurs.

    Centraliser ce queryset évite les divergences entre les vues et garantit
    que la page détail bénéficie toujours des mêmes optimisations.

    Retour
    ------
    QuerySet[Film]
        Queryset de films enrichi avec les relations nécessaires à l'affichage
        détaillé.

    Points d'attention
    ------------------
    - `select_related("genre")` est adapté car un film possède un seul genre.
    - `prefetch_related("acteurs")` est adapté car un film peut avoir plusieurs
      acteurs.
    - `Prefetch("critiques", queryset=_critique_queryset())` permet de contrôler
      précisément la manière dont les critiques et leurs dépendances sont chargées.
    """
    return Film.objects.select_related("genre").prefetch_related(
        "acteurs",
        Prefetch("critiques", queryset=_critique_queryset()),
    )


def _films_mieux_notes(limit):
    """
    Retourne les films les mieux notés, dans la limite demandée.

    Paramètres
    ----------
    limit
        Nombre maximum de films à retourner.

    Logique métier
    --------------
    Un film est considéré comme classable parmi les mieux notés uniquement si :
    - sa note moyenne n'est pas nulle ;
    - il possède au moins une critique.

    Cette double condition évite d'afficher :
    - les films qui n'ont encore jamais été évalués ;
    - les films dont la note moyenne serait absente ;
    - les données incohérentes ou incomplètes.

    Ordre de tri
    ------------
    Les films sont triés par :
    1. note moyenne décroissante ;
    2. nombre de critiques décroissant ;
    3. titre alphabétique croissant.

    Ce dernier critère rend le tri déterministe lorsque deux films ont la même
    note moyenne et le même nombre de critiques.

    Retour
    ------
    QuerySet[Film]
        Queryset limité aux meilleurs films selon les critères définis.

    Effets de bord
    --------------
    Aucun effet de bord. La base est interrogée uniquement lorsque le queryset
    est évalué.
    """
    return (
        Film.objects.select_related("genre")
        .filter(note_moyenne__isnull=False, nombre_critiques__gt=0)
        .order_by("-note_moyenne", "-nombre_critiques", "titre")[:limit]
    )


def _films_populaires(limit):
    """
    Retourne les films les plus populaires, dans la limite demandée.

    Paramètres
    ----------
    limit
        Nombre maximum de films à retourner.

    Logique métier
    --------------
    Ici, la popularité est déduite du nombre de critiques publiées sur un film.
    Un film doit donc avoir au moins une critique pour être considéré comme
    populaire.

    Ordre de tri
    ------------
    Les films sont triés par :
    1. nombre de critiques décroissant ;
    2. note moyenne décroissante ;
    3. titre alphabétique croissant.

    Ce classement favorise d'abord l'engagement des utilisateurs, puis la qualité
    moyenne du film, puis un tri stable par titre.

    Retour
    ------
    QuerySet[Film]
        Queryset limité aux films les plus commentés/critiqués.

    Point d'attention
    -----------------
    `note_moyenne` peut être nulle pour certains films, mais le filtre
    `nombre_critiques__gt=0` devrait normalement garantir que les films retournés
    disposent de critiques. Le modèle ou les signaux applicatifs doivent maintenir
    la cohérence entre `nombre_critiques` et `note_moyenne`.
    """
    return (
        Film.objects.select_related("genre")
        .filter(nombre_critiques__gt=0)
        .order_by("-nombre_critiques", "-note_moyenne", "titre")[:limit]
    )


def _prepare_comment_forms(critiques, user, bound_form=None, target_id=None):
    """
    Prépare les formulaires de commentaire associés aux critiques affichées.

    Paramètres
    ----------
    critiques
        Liste ou itérable de critiques affichées sur la page détail.
    user
        Utilisateur courant provenant de `request.user`.
    bound_form
        Formulaire lié à des données POST, généralement invalide, à réafficher
        avec ses erreurs.
    target_id
        Identifiant de la critique ciblée par le formulaire lié.

    Rôle
    ----
    La page détail peut afficher plusieurs critiques. Chaque critique peut avoir
    son propre formulaire de commentaire. Cette fonction attache dynamiquement
    un attribut `comment_form` à chaque objet critique afin que le template puisse
    afficher le bon formulaire au bon endroit.

    Cas utilisateur anonyme
    -----------------------
    Si l'utilisateur n'est pas authentifié, la fonction s'arrête immédiatement.
    Cela évite de préparer des formulaires destinés à publier des commentaires
    alors que l'utilisateur n'a pas le droit de le faire.

    Gestion des erreurs de formulaire
    ---------------------------------
    Lorsqu'un commentaire invalide est soumis, la vue doit réafficher la page
    détail en montrant les erreurs uniquement sous la critique concernée.
    C'est le rôle de `bound_form` et `target_id`.

    Effets de bord
    --------------
    Cette fonction modifie en mémoire les objets `critique` reçus en leur ajoutant
    un attribut dynamique `comment_form`. Elle ne modifie pas la base de données.
    """
    # Les utilisateurs anonymes peuvent lire les critiques et commentaires,
    # mais ils ne doivent pas recevoir de formulaire de publication.
    if not user.is_authenticated:
        return

    # Parcours de chaque critique affichée afin d'attacher le formulaire adapté.
    for critique in critiques:
        # Si cette critique correspond à celle qui a reçu un formulaire invalide,
        # on réutilise le formulaire lié afin de conserver les données saisies
        # et les messages d'erreur.
        if critique.pk == target_id:
            critique.comment_form = bound_form
        else:
            # Pour les autres critiques, on crée un formulaire vierge.
            # `auto_id` personnalise les identifiants HTML afin d'éviter plusieurs
            # champs ayant le même id dans une page contenant plusieurs formulaires.
            critique.comment_form = CommentForm(auto_id=f"id_%s_{critique.pk}")


def _detail_url(film_id, critique_id=None):
    """
    Construit l'URL de détail d'un film, avec ancre optionnelle vers une critique.

    Paramètres
    ----------
    film_id
        Identifiant du film à afficher.
    critique_id
        Identifiant optionnel de la critique à cibler dans la page.

    Retour
    ------
    str
        URL de la page détail du film. Si `critique_id` est fourni, l'URL contient
        une ancre HTML de la forme `#critique-<id>`.

    Utilité
    -------
    Après la création, modification ou suppression d'une critique ou d'un
    commentaire, l'utilisateur doit être redirigé vers l'endroit pertinent de la
    page. Cette fonction évite de dupliquer la construction de ces URL.
    """
    # Génère l'URL nommée de la page détail à partir de la configuration d'URL.
    url = reverse("movies:film_detail", args=[film_id])

    # Si une critique est ciblée, on ajoute une ancre HTML pour repositionner
    # directement le navigateur sur cette critique.
    if critique_id:
        return f"{url}#critique-{critique_id}"

    # Sans critique ciblée, on retourne simplement l'URL du détail film.
    return url


def _user_review_from_critiques(critiques, user):
    """
    Recherche la critique déjà publiée par l'utilisateur courant.

    Paramètres
    ----------
    critiques
        Liste ou itérable de critiques déjà chargées pour le film.
    user
        Utilisateur courant provenant de `request.user`.

    Retour
    ------
    Critique | None
        La critique appartenant à l'utilisateur connecté si elle existe,
        sinon `None`.

    Logique métier
    --------------
    Un utilisateur ne doit normalement publier qu'une seule critique par film.
    Cette fonction permet au template de savoir s'il doit afficher :
    - un bouton "Ajouter une critique" ;
    - ou une indication indiquant que l'utilisateur a déjà publié une critique,
      avec éventuellement un lien de modification.

    Cas utilisateur anonyme
    -----------------------
    Si l'utilisateur n'est pas connecté, aucune critique personnelle ne peut être
    associée. La fonction retourne donc immédiatement `None`.

    Choix technique
    ---------------
    La fonction cherche dans la liste `critiques` déjà préchargée au lieu de
    refaire une requête SQL. Cela évite une requête inutile sur la page détail.
    """
    # Un utilisateur anonyme n'a pas de critique personnelle.
    if not user.is_authenticated:
        return None

    # Recherche la première critique dont l'utilisateur correspond à l'utilisateur
    # actuellement connecté.
    return next(
        (
            critique
            for critique in critiques
            if critique.utilisateur_id == user.id
        ),
        None,
    )


def _review_form_context(film, form, form_title, submit_label, critique=None):
    """
    Prépare le contexte commun des pages de création et modification de critique.

    Paramètres
    ----------
    film
        Film concerné par la critique.
    form
        Instance du formulaire de critique.
    form_title
        Titre affiché dans la page du formulaire.
    submit_label
        Libellé du bouton de soumission.
    critique
        Critique existante dans le cas d'une modification. Vaut `None` lors
        d'une création.

    Retour
    ------
    dict
        Dictionnaire de contexte transmis au template `movies/review_form.html`.

    Objectif
    --------
    La création et la modification d'une critique utilisent le même template.
    Cette fonction factorise donc les variables communes tout en permettant de
    personnaliser le titre et le bouton selon le cas.
    """
    return {
        "film": film,
        "form": form,
        "critique": critique,
        "form_title": form_title,
        "submit_label": submit_label,
    }


# ============================================================================
# Vue d'accueil
# ============================================================================
#
# Cette vue affiche une page synthétique avec :
# - quelques films populaires ;
# - quelques films les mieux notés ;
# - des statistiques globales sur le nombre de films et de critiques.


class HomeView(TemplateView):
    """Page d'accueil avec films populaires et films les mieux notés."""

    # Template HTML rendu par cette vue.
    template_name = "movies/home.html"

    def get_context_data(self, **kwargs):
        """
        Construit le contexte de la page d'accueil.

        Paramètres
        ----------
        **kwargs
            Données transmises par la classe parente `TemplateView`.

        Retour
        ------
        dict
            Contexte enrichi avec les listes de films et statistiques globales.

        Données ajoutées au contexte
        ----------------------------
        films_populaires
            Les 4 films les plus populaires.
        films_mieux_notes
            Les 4 films les mieux notés.
        nombre_films
            Nombre total de films dans la base.
        nombre_critiques
            Nombre total de critiques publiées.

        Point d'attention
        -----------------
        Les fonctions `_films_populaires` et `_films_mieux_notes` retournent des
        querysets limités. Selon le template, ils seront évalués lors de
        l'itération.
        """
        # Récupère d'abord le contexte standard de TemplateView.
        context = super().get_context_data(**kwargs)

        # Ajoute les données spécifiques à la page d'accueil.
        context.update({
            "films_populaires": _films_populaires(4),
            "films_mieux_notes": _films_mieux_notes(4),
            "nombre_films": Film.objects.count(),
            "nombre_critiques": Critique.objects.count(),
        })

        return context


# ============================================================================
# Vue catalogue des films
# ============================================================================
#
# Cette vue affiche tous les films et permet à l'utilisateur de filtrer la liste
# selon plusieurs critères présents dans la query string :
# - genre ;
# - année de sortie ;
# - note minimale ;
# - recherche textuelle simple.
#
# Exemple d'URL possible :
# /films/?q=Action&genre=1&annee=2024&note_min=4


class MovieListView(TemplateView):
    """Catalogue de films avec recherche et filtres."""

    # Template HTML du catalogue.
    template_name = "movies/movie_list.html"

    def get_context_data(self, **kwargs):
        """
        Construit le contexte du catalogue de films avec application des filtres.

        Paramètres
        ----------
        **kwargs
            Données transmises par la classe parente.

        Retour
        ------
        dict
            Contexte contenant :
            - la liste filtrée des films ;
            - les genres disponibles ;
            - les années disponibles ;
            - le nombre de films correspondant ;
            - les valeurs de recherche et filtres conservées pour l'affichage du formulaire.

        Validation des filtres
        ----------------------
        Les valeurs reçues depuis `request.GET` sont toujours considérées comme
        non fiables. Chaque filtre est donc validé avant application :
        - le genre doit être numérique et correspondre à un genre existant ;
        - l'année doit être numérique et appartenir aux années présentes en base ;
        - la note minimale doit être convertible en Decimal, finie et comprise
          entre 0 et 5.

        Comportement en cas de filtre invalide
        --------------------------------------
        Si un filtre est invalide, il est ignoré et sa valeur sélectionnée est
        réinitialisée à une chaîne vide. Cela évite de bloquer l'affichage du
        catalogue à cause d'une URL manipulée ou incorrecte.
        """
        # Contexte initial fourni par TemplateView.
        context = super().get_context_data(**kwargs)

        # Queryset de départ : tous les films, avec le genre préchargé pour
        # éviter des requêtes supplémentaires lors de l'affichage. On précharge
        # aussi les acteurs car la recherche peut interroger leur nom.
        films = Film.objects.select_related("genre").prefetch_related("acteurs").all()

        # Liste des genres disponibles pour alimenter le formulaire de filtre.
        genres = Genre.objects.all()

        # Extraction des années de sortie existantes en base, dans l'ordre décroissant.
        # `Film.objects.dates(...)` retourne des objets date tronqués à l'année.
        annees = [date.year for date in Film.objects.dates("date_sortie", "year", order="DESC")]

        # Ensemble des identifiants de genres valides.
        # L'utilisation d'un set rend le test d'appartenance rapide.
        genre_ids = set(genres.values_list("id", flat=True))

        # Ensemble des années valides présentes dans la base.
        annees_valides = set(annees)

        # Récupération et nettoyage des valeurs de filtres depuis la query string.
        selected_genre = self.request.GET.get("genre", "").strip()
        selected_annee = self.request.GET.get("annee", "").strip()
        selected_note_min = self.request.GET.get("note_min", "").strip()
        # Recherche texte simple
        selected_q = self.request.GET.get("q", "").strip()

        # Application du filtre par genre uniquement si l'identifiant est valide.
        if selected_genre.isdigit() and int(selected_genre) in genre_ids:
            films = films.filter(genre_id=int(selected_genre))
        else:
            # Réinitialisation de la valeur affichée dans le formulaire si invalide.
            selected_genre = ""

        # Application du filtre par année uniquement si l'année existe en base.
        if selected_annee.isdigit() and int(selected_annee) in annees_valides:
            films = films.filter(date_sortie__year=int(selected_annee))
        else:
            # Réinitialisation de la valeur affichée si l'année est invalide.
            selected_annee = ""

        # Application du filtre par note minimale seulement si une valeur a été fournie.
        if selected_note_min:
            try:
                # Conversion en Decimal pour éviter les problèmes de précision des floats.
                note_valeur = Decimal(selected_note_min)
            except (InvalidOperation, ValueError):
                # Toute valeur non convertible est considérée comme invalide.
                note_valeur = None

            # La note minimale doit être un nombre fini dans l'intervalle métier 0 à 5.
            if note_valeur is not None and note_valeur.is_finite() and Decimal("0") <= note_valeur <= Decimal("5"):
                films = films.filter(note_moyenne__gte=note_valeur)
            else:
                # Réinitialisation de la valeur affichée si la note est invalide.
                selected_note_min = ""

        # Application de la recherche textuelle simple lorsque fournie.
        # Recherche sur : titre, nom de genre, nom des acteurs, et année si la
        # saisie ressemble à une année.
        if selected_q:
            # Construit un filtre OR sur les champs ciblés.
            recherche_filter = (
                Q(titre__icontains=selected_q)
                | Q(genre__nom__icontains=selected_q)
                | Q(acteurs__nom__icontains=selected_q)
            )

            if selected_q.isdigit() and len(selected_q) == 4:
                recherche_filter |= Q(date_sortie__year=int(selected_q))

            # Applique le filtre puis distinct() pour éviter les doublons
            # si plusieurs acteurs correspondent ou plusieurs relations.
            films = films.filter(recherche_filter).distinct()

        # Ajout des données nécessaires au template du catalogue.
        context.update({
            "films": films,
            "genres": genres,
            "annees": annees,
            "nombre_films": films.count(),
            "selected_genre": selected_genre,
            "selected_annee": selected_annee,
            "selected_note_min": selected_note_min,
            "selected_q": selected_q,
        })

        return context


# ============================================================================
# Vue détail d'un film
# ============================================================================
#
# Cette vue affiche :
# - les informations principales du film ;
# - son genre ;
# - ses acteurs ;
# - ses critiques ;
# - les commentaires sous chaque critique ;
# - un formulaire de commentaire par critique pour les utilisateurs connectés ;
# - l'état de la critique déjà publiée par l'utilisateur courant, le cas échéant.


class FilmDetailView(DetailView):

    """Page de détail minimale d'un film, accessible depuis le catalogue."""

    """Affiche un film, ses critiques et les commentaires associés."""

    # Modèle utilisé par DetailView pour récupérer l'objet principal.
    model = Film

    # Template HTML utilisé pour afficher le détail du film.
    template_name = "movies/movie_detail.html"


    def get_queryset(self):
        """
        Retourne le queryset optimisé utilisé par la vue détail.

        Retour
        ------
        QuerySet[Film]
            Queryset préchargeant le genre, les acteurs, les critiques et les
            commentaires nécessaires à l'affichage complet de la page.

        Pourquoi surcharger get_queryset ?
        ----------------------------------
        `DetailView` récupère automatiquement un objet à partir de l'URL.
        En surchargeant `get_queryset`, on contrôle la manière dont cet objet
        est récupéré, notamment les relations à précharger pour optimiser le rendu.
        """
        return _film_detail_queryset()

    def get_context_data(self, **kwargs):
        """
        Enrichit le contexte du détail film.

        Paramètres
        ----------
        **kwargs
            Données fournies par la classe parente, incluant généralement `object`.

        Retour
        ------
        dict
            Contexte contenant notamment :
            - `critiques` : liste des critiques du film ;
            - `user_review` : critique de l'utilisateur courant si elle existe.

        Effets de bord
        --------------
        La fonction `_prepare_comment_forms` ajoute dynamiquement un attribut
        `comment_form` sur les objets critiques en mémoire pour faciliter le rendu
        du template.
        """
        # Récupère le contexte standard de DetailView, contenant notamment le film.
        context = super().get_context_data(**kwargs)

        # Transforme les critiques préchargées en liste afin de les parcourir
        # plusieurs fois sans réévaluer le queryset.
        critiques = list(self.object.critiques.all())

        # Ajoute les formulaires de commentaire aux critiques si l'utilisateur
        # est authentifié.
        _prepare_comment_forms(critiques, self.request.user)

        # Expose explicitement les critiques au template.
        context["critiques"] = critiques

        # Recherche la critique déjà publiée par l'utilisateur courant.
        context["user_review"] = _user_review_from_critiques(
            critiques,
            self.request.user,
        )

        return context


# ============================================================================
# Vue de création d'une critique
# ============================================================================
#
# Cette vue permet à un utilisateur connecté de publier une critique sur un film.
# Elle impose une règle métier importante : un utilisateur ne peut publier qu'une
# seule critique par film.


@login_required
def review_create(request, film_id):
    """Publie une critique unique pour le film visé."""

    # Récupération du film cible depuis l'identifiant présent dans l'URL.
    # Le genre et les acteurs sont préchargés pour l'affichage éventuel du formulaire.
    film = get_object_or_404(
        Film.objects.select_related("genre").prefetch_related("acteurs"),
        pk=film_id,
    )

    # Vérifie si l'utilisateur connecté a déjà publié une critique sur ce film.
    existing_review = Critique.objects.filter(
        film=film,
        utilisateur=request.user,
    ).first()

    # Si une critique existe déjà, on empêche la création d'un doublon.
    if existing_review:
        messages.info(
            request,
            "Vous avez déjà publié une critique pour ce film.",
        )
        return redirect(_detail_url(film.pk, existing_review.pk))

    # Traitement du formulaire soumis.
    if request.method == "POST":
        # Le formulaire reçoit uniquement les données POST.
        # Les champs sensibles comme `film` et `utilisateur` seront imposés côté serveur.
        form = ReviewForm(request.POST)

        # Validation du formulaire selon les règles définies dans ReviewForm.
        if form.is_valid():
            # `commit=False` permet de créer l'objet sans l'enregistrer immédiatement.
            # C'est nécessaire pour ajouter le film et l'utilisateur côté serveur.
            critique = form.save(commit=False)

            # Association sécurisée au film ciblé par l'URL.
            critique.film = film

            # Association sécurisée à l'utilisateur connecté.
            critique.utilisateur = request.user

            # Enregistrement définitif en base.
            critique.save()

            # Message de confirmation affiché après redirection.
            messages.success(request, "Votre critique a été publiée.")

            # Redirection vers la critique nouvellement créée.
            return redirect(_detail_url(film.pk, critique.pk))
    else:
        # Pour une requête GET, on affiche un formulaire vierge.
        form = ReviewForm()

    # Affichage du formulaire de création si GET ou si POST invalide.
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


# ============================================================================
# Vue de modification d'une critique
# ============================================================================
#
# Cette vue permet à un utilisateur connecté de modifier uniquement ses propres
# critiques. La restriction est appliquée dans la requête de récupération avec
# `utilisateur=request.user`.


@login_required
def review_update(request, critique_id):
    """Modifie une critique appartenant à l'utilisateur connecté."""

    # Récupère la critique uniquement si elle appartient à l'utilisateur connecté.
    # Sinon, Django renvoie une 404, ce qui évite d'exposer l'existence d'une
    # critique appartenant à un autre utilisateur.
    critique = get_object_or_404(
        Critique.objects.select_related("film__genre", "utilisateur")
        .prefetch_related("film__acteurs"),
        pk=critique_id,
        utilisateur=request.user,
    )

    # Raccourci vers le film associé, utilisé pour le template et la redirection.
    film = critique.film

    # Traitement d'une soumission de formulaire.
    if request.method == "POST":
        # Le formulaire est lié à l'instance existante, ce qui déclenche une mise
        # à jour au lieu d'une création.
        form = ReviewForm(request.POST, instance=critique)

        if form.is_valid():
            # Sauvegarde des modifications validées.
            critique = form.save()

            # Message de succès affiché après redirection.
            messages.success(request, "Votre critique a été mise à jour.")

            # Retour vers la critique modifiée.
            return redirect(_detail_url(film.pk, critique.pk))
    else:
        # En GET, le formulaire est prérempli avec les données existantes.
        form = ReviewForm(instance=critique)

    # Affiche le formulaire de modification.
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


# ============================================================================
# Vue de suppression d'une critique
# ============================================================================
#
# Cette vue suit un fonctionnement classique en deux étapes :
# - GET : affiche une page de confirmation ;
# - POST : supprime réellement la critique.
#
# Comme pour la modification, l'utilisateur ne peut supprimer que ses propres
# critiques.


@login_required
def review_delete(request, critique_id):
    """Confirme puis supprime une critique appartenant à l'utilisateur."""

    # Récupère la critique uniquement si elle appartient à l'utilisateur connecté.
    critique = get_object_or_404(
        Critique.objects.select_related("film__genre", "utilisateur")
        .prefetch_related("film__acteurs"),
        pk=critique_id,
        utilisateur=request.user,
    )

    # Conserve le film avant suppression pour pouvoir rediriger après `delete`.
    film = critique.film

    # La suppression effective n'est réalisée que via POST.
    if request.method == "POST":
        # Suppression de la critique en base.
        # Selon l'implémentation du modèle, cette suppression peut déclencher
        # un recalcul des statistiques du film.
        critique.delete()

        # Message de confirmation.
        messages.success(request, "Votre critique a été supprimée.")

        # Retour vers la page détail du film, sans ancre de critique supprimée.
        return redirect(_detail_url(film.pk))

    # En GET, on affiche une page de confirmation sans supprimer la critique.
    return render(
        request,
        "movies/review_confirm_delete.html",
        {
            "film": film,
            "critique": critique,
        },
    )


# ============================================================================
# Vue d'ajout de commentaire
# ============================================================================
#
# Cette vue permet à un utilisateur connecté de publier un commentaire sous une
# critique précise.
#
# Sécurité importante
# -------------------
# La critique ciblée est déterminée uniquement par l'identifiant présent dans
# l'URL (`critique_id`). Même si un utilisateur tente d'envoyer une autre critique
# ou un autre utilisateur dans les données POST, ces valeurs ne sont pas utilisées.


@login_required
@require_POST
def ajouter_commentaire(request, critique_id):
    """Publie un commentaire sous la critique visée par l'URL uniquement."""

    # Récupère la critique cible.
    # Le film est préchargé car son identifiant est nécessaire à la redirection.
    critique = get_object_or_404(
        Critique.objects.select_related("film"),
        pk=critique_id,
    )

    # Crée un formulaire lié aux données POST.
    # L'auto_id personnalisé garantit que l'identifiant HTML du champ est cohérent
    # avec celui utilisé sur la page détail pour cette critique précise.
    form = CommentForm(request.POST, auto_id=f"id_%s_{critique.pk}")

    # Si le commentaire respecte les règles de validation du formulaire.
    if form.is_valid():
        # Création de l'objet commentaire sans enregistrement immédiat.
        commentaire = form.save(commit=False)

        # Association sécurisée à la critique ciblée par l'URL.
        commentaire.critique = critique

        # Association sécurisée à l'utilisateur connecté.
        commentaire.utilisateur = request.user

        # Enregistrement en base.
        commentaire.save()

        # Message de succès affiché après redirection.
        messages.success(request, "Votre commentaire a été publié.")

        # Construction de l'URL de détail du film.
        detail_url = reverse("movies:film_detail", args=[critique.film_id])

        # Redirection vers l'ancre de la critique commentée.
        return redirect(f"{detail_url}#critique-{critique.pk}")

    # Si le formulaire est invalide, il faut réafficher toute la page détail
    # avec les critiques, les commentaires et l'erreur du formulaire au bon endroit.
    film = get_object_or_404(_film_detail_queryset(), pk=critique.film_id)

    # Liste des critiques du film, déjà préchargées via `_film_detail_queryset`.
    critiques = list(film.critiques.all())

    # Réattache les formulaires de commentaire, en plaçant le formulaire invalide
    # précisément sous la critique concernée.
    _prepare_comment_forms(critiques, request.user, form, critique.pk)

    # Réaffiche la page détail avec les erreurs de validation.
    return render(
        request,
        "movies/movie_detail.html",
        {
            "film": film,
            "critiques": critiques,
            "user_review": _user_review_from_critiques(critiques, request.user),
        },
    )


# ============================================================================
# Vue de classement des films
# ============================================================================
#
# Cette vue affiche deux classements plus complets que ceux de la page d'accueil :
# - les films les mieux notés ;
# - les films les plus populaires.
#
# Elle s'appuie sur les mêmes fonctions utilitaires que l'accueil afin de garantir
# une cohérence métier entre les deux pages.


class RankingView(TemplateView):
    """
    Affiche deux classements des films :
    1. Films les mieux notés (par note moyenne décroissante)
    2. Films les plus populaires (par nombre de critiques décroissant)
    """

    # Template HTML dédié aux classements.
    template_name = "movies/ranking.html"

    def get_context_data(self, **kwargs):
        """
        Construit le contexte de la page de classement.

        Paramètres
        ----------
        **kwargs
            Données transmises par `TemplateView`.

        Retour
        ------
        dict
            Contexte contenant :
            - `films_mieux_notes` : les 20 meilleurs films selon la note ;
            - `films_populaires` : les 20 films les plus populaires.

        Différence avec la page d'accueil
        ---------------------------------
        La page d'accueil affiche seulement 4 films dans chaque catégorie pour
        rester synthétique. La page de classement en affiche 20 afin de fournir
        une vue plus complète.
        """
        # Récupération du contexte standard.
        context = super().get_context_data(**kwargs)

        # Ajout des deux classements principaux.
        context.update({
            "films_mieux_notes": _films_mieux_notes(20),
            "films_populaires": _films_populaires(20),
        })

        return context
