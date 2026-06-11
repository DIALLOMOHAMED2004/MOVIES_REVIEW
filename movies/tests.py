# Import standard permettant de construire des dates fixes dans les jeux de données de test.
from datetime import date

# Decimal est utilisé pour comparer des notes moyennes avec précision,
# sans les imprécisions classiques des nombres flottants.
from decimal import Decimal

# Import de l'interface d'administration Django sous un alias explicite.
# L'alias évite toute ambiguïté avec d'éventuels modules locaux nommés "admin".
from django.contrib import admin as django_admin

# Récupère dynamiquement le modèle utilisateur actif du projet.
# Cela respecte la configuration AUTH_USER_MODEL si le projet utilise un modèle personnalisé.
from django.contrib.auth import get_user_model

# Classe de base Django pour écrire des tests unitaires avec base de données de test isolée.
from django.test import TestCase

# Permet de résoudre les noms d'URL Django en URL concrètes.
# Les tests restent ainsi robustes si les chemins d'URL changent mais que les noms restent identiques.
from django.urls import reverse

# Import des modèles métier utilisés par les tests.
# Ces modèles représentent les entités principales du domaine Movie Review.
from .models import Acteur, Casting, Commentaire, Critique, Film, Genre


# Modèle utilisateur réellement utilisé par l'application.
# Tous les tests qui créent des comptes passent par cette référence pour rester compatibles
# avec un éventuel modèle utilisateur personnalisé.
User = get_user_model()


# ============================================================================
# Tests Phase 6 — Page de classement des films
# ============================================================================
#
# Cette classe vérifie le comportement de la vue de classement.
# Elle contrôle notamment :
# - l'existence des deux classements attendus ;
# - l'exclusion des films sans critique ;
# - l'ordre des films les mieux notés ;
# - l'ordre des films les plus populaires ;
# - la présence de liens vers les pages de détail.
#
# Chaque test fonctionne sur une base de données temporaire créée par Django.
class Phase6RankingViewTests(TestCase):

    # Prépare les données communes à tous les tests de cette classe.
    # Cette méthode est exécutée avant chaque méthode test_* afin de garantir
    # l'isolation complète des tests.
    def setUp(self):
        # Genre commun utilisé pour rattacher tous les films créés dans ce scénario.
        self.genre = Genre.objects.create(nom="Drame")

        # Film ayant la meilleure note moyenne parmi les films avec critiques.
        # Il doit apparaître en première position dans le classement par note.
        self.top_note = Film.objects.create(
            titre="Zeta top",
            synopsis="Film le mieux note.",
            genre=self.genre,
            date_sortie=date(2024, 1, 1),
            duree_minutes=120,
            note_moyenne=Decimal("5.00"),
            nombre_critiques=1,
        )

        # Film avec une bonne note et un nombre de critiques plus élevé.
        # Il permet de vérifier que le classement par note et le classement par popularité
        # ne répondent pas aux mêmes critères.
        self.bonne_note_populaire = Film.objects.create(
            titre="Bonne note populaire",
            synopsis="Film bien note et populaire.",
            genre=self.genre,
            date_sortie=date(2023, 1, 1),
            duree_minutes=118,
            note_moyenne=Decimal("4.50"),
            nombre_critiques=5,
        )

        # Premier film d'un cas d'égalité.
        # Il sert à vérifier le critère secondaire de tri lorsque note et nombre de critiques
        # sont identiques à ceux d'un autre film.
        self.alpha_ex_aequo = Film.objects.create(
            titre="Alpha ex aequo",
            synopsis="Film en egalite.",
            genre=self.genre,
            date_sortie=date(2022, 1, 1),
            duree_minutes=105,
            note_moyenne=Decimal("4.00"),
            nombre_critiques=3,
        )

        # Deuxième film d'un cas d'égalité.
        # Son titre permet de vérifier que le tri alphabétique éventuel est stable et attendu.
        self.beta_ex_aequo = Film.objects.create(
            titre="Beta ex aequo",
            synopsis="Autre film en egalite.",
            genre=self.genre,
            date_sortie=date(2021, 1, 1),
            duree_minutes=107,
            note_moyenne=Decimal("4.00"),
            nombre_critiques=3,
        )

        # Film ayant le plus grand nombre de critiques.
        # Il doit apparaître en première position dans le classement de popularité.
        self.plus_populaire = Film.objects.create(
            titre="Plus populaire",
            synopsis="Film avec le plus de critiques.",
            genre=self.genre,
            date_sortie=date(2020, 1, 1),
            duree_minutes=130,
            note_moyenne=Decimal("3.00"),
            nombre_critiques=10,
        )

        # Film sans aucune critique.
        # Il doit être exclu des classements car un film non évalué ne doit pas être classé.
        self.sans_critique = Film.objects.create(
            titre="Sans critique",
            synopsis="Film sans avis.",
            genre=self.genre,
            date_sortie=date(2019, 1, 1),
            duree_minutes=90,
            note_moyenne=None,
            nombre_critiques=0,
        )

        # Cas incohérent volontaire : une note moyenne est présente alors que le nombre
        # de critiques est nul. Le test vérifie que l'application se base bien sur
        # nombre_critiques pour décider si un film est classable.
        self.note_sans_critique = Film.objects.create(
            titre="Note incoherente sans critique",
            synopsis="Film sans critique malgre une note stockee.",
            genre=self.genre,
            date_sortie=date(2018, 1, 1),
            duree_minutes=95,
            note_moyenne=Decimal("5.00"),
            nombre_critiques=0,
        )

    # Vérifie que la page de classement répond correctement et fournit les deux listes attendues.
    def test_ranking_page_displays_both_rankings(self):
        response = self.client.get(reverse("movies:classement"))

        # La vue doit être accessible sans erreur.
        self.assertEqual(response.status_code, 200)

        # Le contexte doit contenir le classement par note.
        self.assertIn("films_mieux_notes", response.context)

        # Le contexte doit contenir le classement par popularité.
        self.assertIn("films_populaires", response.context)

        # Le rendu HTML doit afficher le titre de section des films les mieux notés.
        self.assertContains(response, "Films les mieux notés")

        # Le rendu HTML doit afficher le titre de section des films les plus populaires.
        self.assertContains(response, "Films les plus populaires")

    # Vérifie que les films sans critique sont exclus de tous les classements.
    def test_ranking_excludes_films_without_reviews(self):
        response = self.client.get(reverse("movies:classement"))

        # Conversion en liste pour faciliter les assertions d'appartenance.
        films_mieux_notes = list(response.context["films_mieux_notes"])
        films_populaires = list(response.context["films_populaires"])

        # Le film sans critique ne doit pas apparaître dans le classement par note.
        self.assertNotIn(self.sans_critique, films_mieux_notes)

        # Le film sans critique ne doit pas apparaître dans le classement par popularité.
        self.assertNotIn(self.sans_critique, films_populaires)

        # Même avec une note stockée, un film sans critique réelle doit être exclu.
        self.assertNotIn(self.note_sans_critique, films_mieux_notes)

        # Même règle pour le classement par popularité.
        self.assertNotIn(self.note_sans_critique, films_populaires)

    # Vérifie l'ordre exact attendu du classement des films les mieux notés.
    def test_top_rated_ranking_uses_expected_order(self):
        response = self.client.get(reverse("movies:classement"))

        # L'ordre attendu combine la note moyenne, le nombre de critiques et un critère
        # de départage déterministe pour les ex aequo.
        self.assertEqual(
            list(response.context["films_mieux_notes"]),
            [
                self.top_note,
                self.bonne_note_populaire,
                self.alpha_ex_aequo,
                self.beta_ex_aequo,
                self.plus_populaire,
            ],
        )

    # Vérifie l'ordre exact attendu du classement des films les plus populaires.
    def test_popular_ranking_uses_expected_order(self):
        response = self.client.get(reverse("movies:classement"))

        # Le classement populaire privilégie le nombre de critiques avant la note.
        self.assertEqual(
            list(response.context["films_populaires"]),
            [
                self.plus_populaire,
                self.bonne_note_populaire,
                self.alpha_ex_aequo,
                self.beta_ex_aequo,
                self.top_note,
            ],
        )

    # Vérifie que les cartes ou lignes de classement permettent d'accéder au détail d'un film.
    def test_ranking_page_contains_detail_links(self):
        response = self.client.get(reverse("movies:classement"))

        self.assertContains(
            response,
            reverse("movies:film_detail", args=[self.top_note.pk]),
        )


# ============================================================================
# Tests Phase 6 — Page d'accueil
# ============================================================================
#
# Cette classe vérifie que la page d'accueil présente correctement les points d'entrée
# vers le catalogue et le classement, ainsi que des extraits de films classés.
class Phase6HomeViewTests(TestCase):

    # Prépare un petit jeu de films permettant de tester les sections de l'accueil.
    def setUp(self):
        # Genre commun pour les films de ce scénario.
        self.genre = Genre.objects.create(nom="Science-fiction")

        # Film principalement utile pour tester la section "films populaires".
        self.film_populaire = Film.objects.create(
            titre="Film populaire",
            synopsis="Film souvent critique.",
            genre=self.genre,
            date_sortie=date(2024, 5, 1),
            duree_minutes=122,
            note_moyenne=Decimal("4.00"),
            nombre_critiques=7,
        )

        # Film principalement utile pour tester la section "films mieux notés".
        self.film_mieux_note = Film.objects.create(
            titre="Film mieux note",
            synopsis="Film tres bien note.",
            genre=self.genre,
            date_sortie=date(2023, 5, 1),
            duree_minutes=119,
            note_moyenne=Decimal("4.80"),
            nombre_critiques=2,
        )

        # Film sans critique, qui doit être absent des sections basées sur les classements.
        self.sans_critique = Film.objects.create(
            titre="Film absent accueil",
            synopsis="Film sans critique.",
            genre=self.genre,
            date_sortie=date(2022, 5, 1),
            duree_minutes=100,
        )

    # Vérifie que l'accueil contient les liens principaux de navigation.
    def test_home_page_displays_entry_points(self):
        response = self.client.get(reverse("movies:accueil"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Explorer le catalogue")
        self.assertContains(response, reverse("movies:films"))
        self.assertContains(response, reverse("movies:classement"))

    # Vérifie que les listes de films classés sont disponibles dans le contexte de l'accueil.
    def test_home_page_context_contains_ranked_films(self):
        response = self.client.get(reverse("movies:accueil"))

        # Le film populaire doit être présent dans la section de popularité.
        self.assertIn(self.film_populaire, list(response.context["films_populaires"]))

        # Le film mieux noté doit être présent dans la section des mieux notés.
        self.assertIn(self.film_mieux_note, list(response.context["films_mieux_notes"]))

        # Un film sans critique ne doit pas apparaître dans les classements de l'accueil.
        self.assertNotIn(self.sans_critique, list(response.context["films_populaires"]))
        self.assertNotIn(self.sans_critique, list(response.context["films_mieux_notes"]))

    # Vérifie que les films classés sont réellement affichés dans le HTML.
    def test_home_page_displays_ranked_films_and_detail_links(self):
        response = self.client.get(reverse("movies:accueil"))

        self.assertContains(response, "Film populaire")
        self.assertContains(response, "Film mieux note")
        self.assertContains(
            response,
            reverse("movies:film_detail", args=[self.film_populaire.pk]),
        )

    # Vérifie l'état vide de la page d'accueil lorsqu'aucun film classable n'existe.
    def test_home_page_displays_empty_states_without_ranked_films(self):
        # Suppression de tous les films afin de simuler une application sans contenu classable.
        Film.objects.all().delete()

        response = self.client.get(reverse("movies:accueil"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aucun film populaire pour le moment")
        self.assertContains(response, "Aucun film noté pour le moment")



# ============================================================================
# Tests — Catalogue des films
# ============================================================================
#
# Cette classe vérifie la page catalogue :
# - affichage de tous les films ;
# - filtrage par genre ;
# - filtrage par année ;
# - filtrage par note minimale ;
# - combinaison de filtres ;
# - gestion des filtres invalides ;
# - état vide ;
# - lien vers le détail.
class MovieListViewTests(TestCase):

    # Prépare deux genres et deux films aux caractéristiques différentes.
    def setUp(self):
        # Genre utilisé pour tester le filtre "Action".
        self.genre_action = Genre.objects.create(nom="Action")

        # Genre utilisé pour tester le filtre "Drame".
        self.genre_drama = Genre.objects.create(nom="Drame")

        # Film noté, rattaché au genre Action.
        # Il sert de cible positive pour les filtres par note et par année.
        self.film_note = Film.objects.create(
            titre="Film noté",
            synopsis="Synopsis 1",
            genre=self.genre_action,
            date_sortie=date(2022, 3, 15),
            duree_minutes=110,
            note_moyenne=Decimal("4.0"),
            nombre_critiques=5,
        )

        # Film sans note, rattaché au genre Drame.
        # Il sert à vérifier que certains filtres l'excluent correctement.
        self.film_sans_note = Film.objects.create(
            titre="Film sans note",
            synopsis="Synopsis 2",
            genre=self.genre_drama,
            date_sortie=date(2021, 7, 10),
            duree_minutes=95,
            note_moyenne=None,
            nombre_critiques=0,
        )

    # Vérifie que la page catalogue affiche tous les films lorsque aucun filtre n'est appliqué.
    def test_films_page_displays_all_films(self):
        response = self.client.get(reverse("movies:films"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Film noté")
        self.assertContains(response, "Film sans note")
        self.assertContains(response, "Catalogue de Films")

    # Vérifie la combinaison du filtre par genre et du filtre par note minimale.
    def test_films_page_filters_by_genre_and_note_min(self):
        response = self.client.get(reverse("movies:films"), {"genre": self.genre_action.id, "note_min": "3"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Film noté")
        self.assertNotContains(response, "Film sans note")
        self.assertContains(response, "1 film")


    # Vérifie le filtrage simple par genre.
    def test_films_page_filters_by_genre(self):
        response = self.client.get(reverse("movies:films"), {"genre": self.genre_drama.id})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Film noté")
        self.assertContains(response, "Film sans note")

    # Vérifie le filtrage simple par année de sortie.
    def test_films_page_filters_by_year(self):
        response = self.client.get(reverse("movies:films"), {"annee": "2022"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Film noté")
        self.assertNotContains(response, "Film sans note")

    # Vérifie le filtrage simple par note minimale.
    def test_films_page_filters_by_note_min(self):
        response = self.client.get(reverse("movies:films"), {"note_min": "4"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Film noté")
        self.assertNotContains(response, "Film sans note")

    # Vérifie que plusieurs critères de filtrage peuvent être combinés.
    def test_films_page_filters_by_combined_criteria(self):
        response = self.client.get(
            reverse("movies:films"),
            {"genre": self.genre_action.id, "annee": "2022", "note_min": "4"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Film noté")
        self.assertNotContains(response, "Film sans note")
        self.assertContains(response, "1 film")

    # Vérifie que les valeurs de filtres invalides sont ignorées proprement.
    def test_films_page_ignores_invalid_filters(self):
        response = self.client.get(
            reverse("movies:films"),
            {"genre": "999", "annee": "1900", "note_min": "9"},
        )
        self.assertEqual(response.status_code, 200)

        # Les films doivent rester affichés, car les filtres invalides ne doivent pas
        # supprimer tout le contenu de manière arbitraire.
        self.assertContains(response, "Film noté")
        self.assertContains(response, "Film sans note")

        # Le contexte doit réinitialiser les valeurs sélectionnées afin que l'interface
        # ne laisse pas croire qu'un filtre invalide est actif.
        self.assertEqual(response.context["selected_genre"], "")
        self.assertEqual(response.context["selected_annee"], "")
        self.assertEqual(response.context["selected_note_min"], "")

    # Vérifie le message d'état vide lorsque des filtres valides ne retournent aucun film.
    def test_films_page_displays_empty_state(self):
        response = self.client.get(
            reverse("movies:films"),
            {"genre": self.genre_drama.id, "note_min": "4"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Film noté")
        self.assertNotContains(response, "Film sans note")
        self.assertContains(response, "Aucun film ne correspond aux filtres")

    # Vérifie que chaque film du catalogue propose un lien vers sa page de détail.
    def test_films_page_contains_detail_link(self):
        response = self.client.get(reverse("movies:films"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("movies:film_detail", args=[self.film_note.pk]))

    # ------------------------------------------------------------------
    # Tests pour la recherche textuelle simple (paramètre `q`)
    # ------------------------------------------------------------------
    def test_films_page_search_by_title(self):
        film = Film.objects.create(
            titre="Unique Search Title",
            synopsis="Recherche titre",
            genre=self.genre_action,
            date_sortie=date(2020, 1, 1),
            duree_minutes=100,
        )

        response = self.client.get(reverse("movies:films"), {"q": "unique search title"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unique Search Title")

    def test_films_page_search_by_synopsis(self):
        film = Film.objects.create(
            titre="Film Syn",
            synopsis="epic space opera",
            genre=self.genre_action,
            date_sortie=date(2021, 5, 1),
            duree_minutes=95,
        )

        response = self.client.get(reverse("movies:films"), {"q": "space"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Film Syn")

    def test_films_page_search_by_genre_name(self):
        response = self.client.get(reverse("movies:films"), {"q": "action"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Film noté")
        self.assertNotContains(response, "Film sans note")

    def test_films_page_search_by_actor_name(self):
        acteur = Acteur.objects.create(nom="Camille Test")
        # Attache l'acteur à un film existant
        self.film_sans_note.acteurs.add(acteur)

        response = self.client.get(reverse("movies:films"), {"q": "Camille"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Film sans note")

    def test_films_page_search_is_case_insensitive(self):
        film = Film.objects.create(
            titre="CaseTest",
            synopsis="Case insensitive check",
            genre=self.genre_action,
            date_sortie=date(2022, 6, 1),
            duree_minutes=90,
        )

        response = self.client.get(reverse("movies:films"), {"q": "casetest"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CaseTest")

    def test_films_page_empty_search_shows_normal_catalog(self):
        response = self.client.get(reverse("movies:films"), {"q": "   "})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Film noté")
        self.assertContains(response, "Film sans note")

    def test_films_page_search_no_results_shows_empty_state(self):
        response = self.client.get(reverse("movies:films"), {"q": "no-such-film-xyz"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aucun film ne correspond aux filtres")

    def test_films_page_search_combined_with_genre(self):
        film = Film.objects.create(
            titre="Combo Film",
            synopsis="Combo",
            genre=self.genre_action,
            date_sortie=date(2022, 1, 1),
            duree_minutes=100,
        )

        response = self.client.get(reverse("movies:films"), {"q": "Combo", "genre": self.genre_action.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Combo Film")

    def test_films_page_search_combined_with_year(self):
        film = Film.objects.create(
            titre="Year Film",
            synopsis="Year filter",
            genre=self.genre_action,
            date_sortie=date(2019, 4, 1),
            duree_minutes=100,
        )

        response = self.client.get(reverse("movies:films"), {"q": "Year", "annee": "2019"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Year Film")

    def test_films_page_search_combined_with_note_min(self):
        film = Film.objects.create(
            titre="Note Film",
            synopsis="Note filter",
            genre=self.genre_action,
            date_sortie=date(2020, 2, 1),
            duree_minutes=100,
            note_moyenne=Decimal("4.5"),
            nombre_critiques=2,
        )

        response = self.client.get(reverse("movies:films"), {"q": "Note", "note_min": "4"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Note Film")

    def test_films_page_search_does_not_duplicate_films(self):
        film = Film.objects.create(
            titre="Dup Film",
            synopsis="Dup",
            genre=self.genre_action,
            date_sortie=date(2021, 3, 1),
            duree_minutes=100,
        )
        # Ajoute deux acteurs qui correspondent tous deux au même terme de recherche
        a1 = Acteur.objects.create(nom="DupActor")
        a2 = Acteur.objects.create(nom="DupActor")
        film.acteurs.add(a1, a2)

        response = self.client.get(reverse("movies:films"), {"q": "DupActor"})
        self.assertEqual(response.status_code, 200)
        # Le queryset exposé au template ne doit contenir qu'une seule occurrence du film
        self.assertEqual(len(response.context["films"]), 1)


# ============================================================================
# Tests Phase 4 — Détail film et cycle de vie des critiques
# ============================================================================
#
# Cette classe couvre les fonctionnalités principales liées aux critiques :
# - affichage du détail d'un film ;
# - invitation à la connexion pour les visiteurs anonymes ;
# - création d'une critique ;
# - protection contre les valeurs forgées côté client ;
# - unicité d'une critique par utilisateur et par film ;
# - modification par l'auteur uniquement ;
# - suppression par l'auteur uniquement ;
# - recalcul des statistiques du film après création, modification ou suppression.
class Phase4ReviewTests(TestCase):
    """Vérifie le détail film et le cycle de vie des critiques."""

    # Prépare les utilisateurs, les films, une critique existante et un commentaire.
    def setUp(self):
        # Utilisateur auteur de la critique initiale.
        self.auteur = User.objects.create_user(
            username="auteur_phase4",
            password="Motdepasse123!",
        )

        # Utilisateur connecté qui n'a pas encore publié de critique sur le film cible.
        self.visiteur = User.objects.create_user(
            username="visiteur_phase4",
            password="Motdepasse123!",
        )

        # Utilisateur tiers utilisé pour tester les tentatives de falsification de données.
        self.autre_utilisateur = User.objects.create_user(
            username="autre_phase4",
            password="Motdepasse123!",
        )

        # Genre du film principal.
        self.genre = Genre.objects.create(nom="Thriller")

        # Film principal utilisé dans les tests de détail et de critique.
        self.film = Film.objects.create(
            titre="Nuit rouge",
            synopsis="Une enquête nocturne dans une ville sous tension.",
            genre=self.genre,
            date_sortie=date(2025, 2, 14),
            duree_minutes=112,
        )

        # Film secondaire utilisé pour vérifier que le serveur impose le bon film
        # lors de la création d'une critique.
        self.autre_film = Film.objects.create(
            titre="Autre cible",
            synopsis="Un autre film pour vérifier les associations serveur.",
            genre=self.genre,
            date_sortie=date(2024, 2, 14),
            duree_minutes=98,
        )

        # Acteur associé au film principal.
        self.acteur = Acteur.objects.create(nom="Camille Durand")

        # Association ManyToMany entre le film et l'acteur.
        self.film.acteurs.add(self.acteur)

        # Critique initiale publiée par l'auteur.
        self.critique = Critique.objects.create(
            film=self.film,
            utilisateur=self.auteur,
            titre="Tension maîtrisée",
            texte="Une critique existante pour la page détail.",
            note=4,
        )

        # Commentaire initial rattaché à la critique.
        self.commentaire = Commentaire.objects.create(
            critique=self.critique,
            utilisateur=self.visiteur,
            texte="Ce commentaire doit rester visible.",
        )

        # URL du détail du film.
        self.detail_url = reverse("movies:film_detail", args=[self.film.pk])

        # URL de création d'une critique pour le film.
        self.create_url = reverse("movies:review_create", args=[self.film.pk])

        # URL de modification de la critique existante.
        self.update_url = reverse("movies:review_update", args=[self.critique.pk])

        # URL de suppression de la critique existante.
        self.delete_url = reverse("movies:review_delete", args=[self.critique.pk])

    # Vérifie que la page détail affiche les informations du film, de ses relations et des avis.
    def test_detail_page_displays_movie_review_and_comment_data(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nuit rouge")
        self.assertContains(response, "Une enquête nocturne")
        self.assertContains(response, "Thriller")
        self.assertContains(response, "Camille Durand")
        self.assertContains(response, "Tension maîtrisée")
        self.assertContains(response, "Ce commentaire doit rester visible.")

    # Vérifie qu'un utilisateur anonyme est invité à se connecter ou à créer un compte.
    def test_detail_invites_anonymous_user_to_login_or_register(self):
        response = self.client.get(self.detail_url)

        self.assertContains(response, "Connectez-vous")
        self.assertContains(response, reverse("accounts:connexion"))
        self.assertContains(response, reverse("accounts:inscription"))

    # Vérifie qu'un utilisateur connecté sans critique existante peut accéder au bouton d'ajout.
    def test_detail_shows_add_review_button_for_user_without_review(self):
        self.client.force_login(self.visiteur)

        response = self.client.get(self.detail_url)

        self.assertContains(response, "Ajouter une critique")
        self.assertContains(response, self.create_url)

    # Vérifie que l'auteur d'une critique voit l'action de modification plutôt que l'ajout.
    def test_detail_shows_edit_review_button_for_review_author(self):
        self.client.force_login(self.auteur)

        response = self.client.get(self.detail_url)

        self.assertContains(response, "Vous avez déjà publié une critique")
        self.assertContains(response, "Modifier ma critique")
        self.assertContains(response, self.update_url)

    # Vérifie qu'un utilisateur authentifié peut créer une critique valide.
    def test_authenticated_user_can_create_review(self):
        self.client.force_login(self.visiteur)

        response = self.client.post(
            self.create_url,
            {
                "titre": "Avis personnel",
                "texte": "Une analyse publiée par un utilisateur connecté.",
                "note": "5",
            },
        )

        # La critique doit être créée avec les données envoyées.
        critique = Critique.objects.get(titre="Avis personnel")

        # Une création réussie doit rediriger vers le détail.
        self.assertEqual(response.status_code, 302)

        # Le film associé doit être celui porté par l'URL, pas une valeur client.
        self.assertEqual(critique.film, self.film)

        # L'utilisateur associé doit être l'utilisateur connecté.
        self.assertEqual(critique.utilisateur, self.visiteur)

        # La redirection cible l'ancre de la nouvelle critique.
        self.assertEqual(response["Location"], f"{self.detail_url}#critique-{critique.pk}")

    # Vérifie qu'un utilisateur anonyme ne peut pas créer de critique.
    def test_anonymous_user_is_redirected_from_create_review(self):
        response = self.client.post(
            self.create_url,
            {
                "titre": "Tentative anonyme",
                "texte": "Cette critique ne doit pas être créée.",
                "note": "3",
            },
        )

        # Django doit rediriger vers la page de connexion avec conservation de next.
        self.assertRedirects(
            response,
            f"{reverse('accounts:connexion')}?next={self.create_url}",
        )

        # Aucune critique ne doit être créée en base.
        self.assertFalse(Critique.objects.filter(titre="Tentative anonyme").exists())

    # Vérifie que les champs sensibles envoyés par le client sont ignorés.
    def test_forged_film_and_user_values_are_ignored_on_create(self):
        self.client.force_login(self.visiteur)

        self.client.post(
            self.create_url,
            {
                "titre": "Associations protégées",
                "texte": "Le serveur impose le film et l'utilisateur.",
                "note": "4",
                "film": self.autre_film.pk,
                "utilisateur": self.autre_utilisateur.pk,
            },
        )

        # Même si le POST contient film/utilisateur, le serveur doit imposer ses propres valeurs.
        critique = Critique.objects.get(titre="Associations protégées")
        self.assertEqual(critique.film, self.film)
        self.assertEqual(critique.utilisateur, self.visiteur)

    # Vérifie qu'un même utilisateur ne peut pas publier deux critiques sur le même film.
    def test_user_cannot_create_two_reviews_for_same_movie(self):
        self.client.force_login(self.auteur)

        response = self.client.post(
            self.create_url,
            {
                "titre": "Doublon",
                "texte": "Cette critique ne doit pas être créée.",
                "note": "5",
            },
            follow=True,
        )

        # L'utilisateur est redirigé vers sa critique existante.
        self.assertRedirects(response, f"{self.detail_url}#critique-{self.critique.pk}")

        # Un message explicite doit informer que la critique existe déjà.
        self.assertContains(response, "Vous avez déjà publié une critique pour ce film.")

        # Le doublon ne doit pas être créé.
        self.assertFalse(Critique.objects.filter(titre="Doublon").exists())

    # Vérifie que la création d'une critique met à jour les statistiques agrégées du film.
    def test_create_review_updates_movie_statistics(self):
        self.client.force_login(self.visiteur)

        self.client.post(
            self.create_url,
            {
                "titre": "Nouvelle note",
                "texte": "Une critique qui change la moyenne.",
                "note": "2",
            },
        )

        # Recharge l'objet depuis la base pour récupérer les valeurs recalculées.
        self.film.refresh_from_db()

        # Deux critiques existent désormais.
        self.assertEqual(self.film.nombre_critiques, 2)

        # Moyenne attendue : ancienne note 4 + nouvelle note 2 = 3.00.
        self.assertEqual(self.film.note_moyenne, Decimal("3.00"))

    # Vérifie que l'auteur d'une critique peut la modifier.
    def test_author_can_update_review(self):
        self.client.force_login(self.auteur)

        response = self.client.post(
            self.update_url,
            {
                "titre": "Titre modifié",
                "texte": "Texte modifié par l'auteur.",
                "note": "5",
            },
        )

        # Recharge la critique pour vérifier les données persistées.
        self.critique.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.critique.titre, "Titre modifié")
        self.assertEqual(response["Location"], f"{self.detail_url}#critique-{self.critique.pk}")

    # Vérifie qu'un autre utilisateur ne peut pas modifier une critique qui ne lui appartient pas.
    def test_other_user_cannot_update_review(self):
        self.client.force_login(self.visiteur)

        response = self.client.post(
            self.update_url,
            {
                "titre": "Modification interdite",
                "texte": "Cette modification ne doit pas passer.",
                "note": "1",
            },
        )

        # La vue masque l'existence de la ressource en répondant 404.
        self.assertEqual(response.status_code, 404)

        # La critique doit rester inchangée.
        self.critique.refresh_from_db()
        self.assertEqual(self.critique.titre, "Tension maîtrisée")

    # Vérifie que modifier la note d'une critique recalcule la moyenne du film.
    def test_update_review_note_updates_movie_statistics_and_message(self):
        self.client.force_login(self.auteur)

        response = self.client.post(
            self.update_url,
            {
                "titre": "Tension maîtrisée",
                "texte": "Une critique existante pour la page détail.",
                "note": "2",
            },
            follow=True,
        )

        self.film.refresh_from_db()

        # Comme il n'y a qu'une critique sur ce film, la moyenne doit devenir 2.00.
        self.assertEqual(self.film.note_moyenne, Decimal("2.00"))

        # L'utilisateur doit recevoir un message de confirmation.
        self.assertContains(response, "Votre critique a été mise à jour.")

    # Vérifie que l'auteur peut accéder à la page de confirmation de suppression.
    def test_author_can_access_delete_confirmation(self):
        self.client.force_login(self.auteur)

        response = self.client.get(self.delete_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirmer la suppression")
        self.assertContains(response, "Supprimer définitivement")

    # Vérifie que l'auteur peut supprimer sa critique via une requête POST.
    def test_author_can_delete_review_with_post(self):
        self.client.force_login(self.auteur)

        response = self.client.post(self.delete_url)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Critique.objects.filter(pk=self.critique.pk).exists())

    # Vérifie qu'un autre utilisateur ne peut pas supprimer la critique.
    def test_other_user_cannot_delete_review(self):
        self.client.force_login(self.visiteur)

        response = self.client.post(self.delete_url)

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Critique.objects.filter(pk=self.critique.pk).exists())

    # Vérifie qu'une requête GET sur la confirmation ne supprime pas la critique.
    def test_get_delete_confirmation_does_not_delete_review(self):
        self.client.force_login(self.auteur)

        response = self.client.get(self.delete_url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Critique.objects.filter(pk=self.critique.pk).exists())

    # Vérifie que la suppression d'une critique recalcule les statistiques du film.
    def test_delete_review_updates_movie_statistics_and_message(self):
        # Ajout d'une seconde critique pour que le recalcul après suppression soit vérifiable.
        Critique.objects.create(
            film=self.film,
            utilisateur=self.visiteur,
            titre="Deuxième avis",
            texte="Une deuxième critique pour vérifier la moyenne.",
            note=2,
        )

        self.client.force_login(self.auteur)

        response = self.client.post(self.delete_url, follow=True)

        self.film.refresh_from_db()

        # Après suppression de la critique note 4, il reste uniquement la critique note 2.
        self.assertEqual(self.film.nombre_critiques, 1)
        self.assertEqual(self.film.note_moyenne, Decimal("2.00"))
        self.assertContains(response, "Votre critique a été supprimée.")


# ============================================================================
# Tests Phase 5 — Commentaires sur les critiques
# ============================================================================
#
# Cette classe vérifie l'intégration des commentaires sur la page détail d'un film.
# Elle couvre :
# - lecture publique des commentaires ;
# - masquage du formulaire pour les anonymes ;
# - obligation d'authentification pour publier ;
# - association serveur du commentaire à la critique et à l'utilisateur connecté ;
# - rejet des commentaires vides ;
# - redirection vers l'ancre de la critique concernée.
class CommentairePhase5Tests(TestCase):
    """Vérifie l'intégration sécurisée des commentaires dans le détail film."""

    # Prépare un film, une critique et un commentaire initial.
    def setUp(self):
        # Auteur de la critique cible.
        self.auteur_critique = User.objects.create_user(
            username="auteur",
            password="Motdepasse123!",
        )

        # Utilisateur qui publiera de nouveaux commentaires.
        self.commentateur = User.objects.create_user(
            username="commentateur",
            password="Motdepasse123!",
        )

        # Utilisateur tiers utilisé pour tester les associations et affichages.
        self.autre_utilisateur = User.objects.create_user(
            username="autre",
            password="Motdepasse123!",
        )

        # Genre local utilisé uniquement dans ce scénario.
        genre = Genre.objects.create(nom="Science-fiction")

        # Film principal.
        self.film = Film.objects.create(
            titre="Voyage orbital",
            synopsis="Une aventure spatiale.",
            genre=genre,
            date_sortie=date(2024, 8, 2),
            duree_minutes=124,
        )

        # Critique cible à laquelle les commentaires seront associés.
        self.critique = Critique.objects.create(
            film=self.film,
            utilisateur=self.auteur_critique,
            titre="Très réussi",
            texte="Une critique de référence.",
            note=4,
        )

        # Commentaire existant visible sur la page détail.
        self.commentaire_existant = Commentaire.objects.create(
            critique=self.critique,
            utilisateur=self.autre_utilisateur,
            texte="Je partage cet avis.",
        )

        # URL du détail film contenant la critique et ses commentaires.
        self.detail_url = reverse("movies:film_detail", args=[self.film.pk])

        # URL de publication d'un commentaire sur la critique cible.
        self.add_url = reverse("movies:ajouter_commentaire", args=[self.critique.pk])

    # Vérifie qu'un visiteur anonyme peut lire les commentaires existants.
    def test_anonymous_user_can_read_existing_comments(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Très réussi")
        self.assertContains(response, "Je partage cet avis.")
        self.assertContains(response, "autre")

    # Vérifie que le formulaire de commentaire est masqué pour les utilisateurs anonymes.
    def test_anonymous_user_does_not_see_comment_form(self):
        response = self.client.get(self.detail_url)

        self.assertNotContains(response, self.add_url)
        self.assertNotContains(response, "Publier le commentaire")
        self.assertContains(response, "Connectez-vous")

        # L'ancre encodée permet de revenir à la critique après connexion.
        self.assertContains(response, f"%23critique-{self.critique.pk}")

    # Vérifie qu'un utilisateur anonyme ne peut pas publier un commentaire via POST.
    def test_anonymous_user_cannot_publish_comment(self):
        response = self.client.post(self.add_url, {"texte": "Tentative anonyme"})

        self.assertRedirects(
            response,
            f"{reverse('accounts:connexion')}?next={self.add_url}",
        )

        # Aucune donnée ne doit être persistée.
        self.assertFalse(
            Commentaire.objects.filter(texte="Tentative anonyme").exists()
        )

    # Vérifie qu'un utilisateur connecté voit un formulaire de commentaire utilisable.
    def test_authenticated_user_sees_comment_form_with_unique_field_id(self):
        self.client.force_login(self.commentateur)

        response = self.client.get(self.detail_url)

        self.assertContains(response, self.add_url)
        self.assertContains(response, "Publier le commentaire")

        # L'identifiant HTML du champ doit être unique par critique pour éviter
        # les conflits lorsqu'une page contient plusieurs formulaires.
        self.assertContains(response, f'id="id_texte_{self.critique.pk}"')

    # Vérifie qu'un utilisateur connecté peut publier un commentaire valide.
    def test_authenticated_user_can_publish_valid_comment(self):
        self.client.force_login(self.commentateur)

        response = self.client.post(self.add_url, {"texte": "Excellent point de vue."})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Commentaire.objects.filter(texte="Excellent point de vue.").exists()
        )

    # Vérifie que le commentaire créé est associé à la critique ciblée par l'URL.
    def test_new_comment_is_associated_with_target_critique(self):
        self.client.force_login(self.commentateur)

        self.client.post(self.add_url, {"texte": "Sur cette critique."})

        commentaire = Commentaire.objects.get(texte="Sur cette critique.")
        self.assertEqual(commentaire.critique, self.critique)

    # Vérifie que le commentaire créé est associé à l'utilisateur connecté.
    def test_new_comment_is_associated_with_logged_in_user(self):
        self.client.force_login(self.commentateur)

        self.client.post(self.add_url, {"texte": "Mon commentaire."})

        commentaire = Commentaire.objects.get(texte="Mon commentaire.")
        self.assertEqual(commentaire.utilisateur, self.commentateur)

    # Vérifie que les valeurs POST forgées pour utilisateur/critique sont ignorées.
    def test_forged_user_and_critique_post_values_are_ignored(self):
        # Création d'une autre critique pour simuler une tentative de détournement.
        autre_critique = Critique.objects.create(
            film=self.film,
            utilisateur=self.autre_utilisateur,
            titre="Autre avis",
            texte="Texte d'une autre critique.",
            note=3,
        )

        self.client.force_login(self.commentateur)

        self.client.post(
            self.add_url,
            {
                "texte": "Associations protégées.",
                "utilisateur": self.autre_utilisateur.pk,
                "critique": autre_critique.pk,
            },
        )

        # Le serveur doit imposer l'utilisateur connecté et la critique de l'URL.
        commentaire = Commentaire.objects.get(texte="Associations protégées.")
        self.assertEqual(commentaire.utilisateur, self.commentateur)
        self.assertEqual(commentaire.critique, self.critique)

    # Vérifie que les commentaires vides ou composés uniquement d'espaces sont refusés.
    def test_blank_or_whitespace_only_comment_is_rejected(self):
        self.client.force_login(self.commentateur)

        # Comptage initial pour vérifier qu'aucun commentaire n'est ajouté.
        initial_count = Commentaire.objects.count()

        response = self.client.post(self.add_url, {"texte": "   \n  "})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Le commentaire ne peut pas être vide.")
        self.assertEqual(Commentaire.objects.count(), initial_count)

    # Vérifie qu'une critique inexistante retourne une erreur 404.
    def test_unknown_critique_returns_404(self):
        self.client.force_login(self.commentateur)

        response = self.client.post(
            reverse("movies:ajouter_commentaire", args=[999999]),
            {"texte": "Introuvable"},
        )

        self.assertEqual(response.status_code, 404)

    # Vérifie que la redirection après succès revient directement sur la critique commentée.
    def test_success_redirect_returns_to_target_critique_anchor(self):
        self.client.force_login(self.commentateur)

        response = self.client.post(self.add_url, {"texte": "Retour ciblé."})

        self.assertEqual(
            response["Location"],
            f"{self.detail_url}#critique-{self.critique.pk}",
        )

    # Vérifie que le formulaire de connexion conserve correctement la destination next.
    def test_login_form_preserves_next_target(self):
        next_target = f"{self.detail_url}#critique-{self.critique.pk}"

        response = self.client.get(
            reverse("accounts:connexion"),
            {"next": next_target},
        )

        self.assertContains(response, 'name="next"')
        self.assertContains(response, f'value="{next_target}"')


# ============================================================================
# Tests Phase 8 — Administration Django et consolidation finale
# ============================================================================
#
# Cette classe vérifie deux aspects liés à l'administration :
# - la configuration des ModelAdmin importants ;
# - le recalcul des statistiques du film lors d'une suppression groupée de critiques.
#
# L'objectif est de s'assurer que l'interface Admin reste cohérente avec les règles métier,
# notamment lorsque des objets sont supprimés en masse depuis Django Admin.
class Phase8AdminTests(TestCase):
    """Vérifie la configuration Admin et la suppression groupée des critiques."""

    # setUpTestData crée des données une seule fois pour toute la classe.
    # Cette approche est plus efficace que setUp lorsque les données sont seulement lues
    # ou lorsque chaque test n'a pas besoin d'un jeu totalement recréé.
    @classmethod
    def setUpTestData(cls):
        # Genre utilisé par le film de test.
        cls.genre = Genre.objects.create(nom="Administration")

        # Film dont les statistiques seront contrôlées après suppression de critiques.
        cls.film = Film.objects.create(
            titre="Film administré",
            synopsis="Film utilisé pour valider la consolidation Admin.",
            genre=cls.genre,
            date_sortie=date(2026, 1, 10),
            duree_minutes=105,
        )

        # Premier auteur de critique.
        cls.auteur_un = User.objects.create(username="admin_auteur_un")

        # Deuxième auteur de critique.
        cls.auteur_deux = User.objects.create(username="admin_auteur_deux")

        # Critique destinée à être supprimée par l'action Admin.
        cls.critique_un = Critique.objects.create(
            film=cls.film,
            utilisateur=cls.auteur_un,
            titre="Avis à supprimer",
            texte="Cette critique sera supprimée depuis l'administration.",
            note=2,
        )

        # Critique qui doit rester après la suppression groupée.
        cls.critique_deux = Critique.objects.create(
            film=cls.film,
            utilisateur=cls.auteur_deux,
            titre="Avis conservé",
            texte="Cette critique doit rester après la suppression groupée.",
            note=4,
        )

    # Vérifie que les modèles importants sont enregistrés et optimisés dans Django Admin.
    def test_important_models_and_admin_options_are_configured(self):
        # Registre interne de Django Admin contenant les ModelAdmin enregistrés.
        registry = django_admin.site._registry

        # Le modèle Casting doit être disponible dans l'administration.
        self.assertIn(Casting, registry)

        # Le ModelAdmin Film doit utiliser select_related sur genre pour éviter
        # des requêtes supplémentaires lors de l'affichage de la liste.
        self.assertEqual(registry[Film].list_select_related, ("genre",))

        # Les statistiques calculées ne doivent pas être modifiables manuellement
        # depuis l'interface Admin.
        self.assertEqual(
            registry[Film].readonly_fields,
            ("note_moyenne", "nombre_critiques"),
        )

        # Le ModelAdmin Critique doit précharger film et utilisateur.
        self.assertEqual(
            registry[Critique].list_select_related,
            ("film", "utilisateur"),
        )

        # Le ModelAdmin Commentaire doit précharger les relations utiles pour afficher
        # les informations liées à la critique, au film et aux utilisateurs.
        self.assertEqual(
            registry[Commentaire].list_select_related,
            ("utilisateur", "critique__film", "critique__utilisateur"),
        )

        # La liste Admin des commentaires doit afficher un extrait lisible.
        self.assertIn("extrait", registry[Commentaire].list_display)

        # La liste Admin des commentaires doit afficher le film concerné.
        self.assertIn("film", registry[Commentaire].list_display)

    # Vérifie qu'une suppression groupée de critiques depuis l'Admin recalcule les statistiques.
    def test_bulk_admin_review_delete_recalculates_movie_statistics(self):
        # Récupération du ModelAdmin associé au modèle Critique.
        critique_admin = django_admin.site._registry[Critique]

        # Simulation directe de l'action de suppression groupée Admin.
        # request=None suffit ici car le test cible la logique métier de delete_queryset.
        critique_admin.delete_queryset(
            request=None,
            queryset=Critique.objects.filter(pk=self.critique_un.pk),
        )

        # Recharge le film afin de lire les statistiques recalculées depuis la base.
        self.film.refresh_from_db()

        # La critique ciblée doit avoir été supprimée.
        self.assertFalse(Critique.objects.filter(pk=self.critique_un.pk).exists())

        # La critique non ciblée doit être conservée.
        self.assertTrue(Critique.objects.filter(pk=self.critique_deux.pk).exists())

        # Il doit rester une seule critique.
        self.assertEqual(self.film.nombre_critiques, 1)

        # La moyenne doit correspondre à la note de la critique restante.
        self.assertEqual(self.film.note_moyenne, Decimal("4.00"))
