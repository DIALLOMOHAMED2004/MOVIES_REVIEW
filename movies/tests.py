from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Commentaire, Critique, Film, Genre


User = get_user_model()


class Phase6RankingViewTests(TestCase):
    def setUp(self):
        self.genre = Genre.objects.create(nom="Drame")
        self.top_note = Film.objects.create(
            titre="Zeta top",
            synopsis="Film le mieux note.",
            genre=self.genre,
            date_sortie=date(2024, 1, 1),
            duree_minutes=120,
            note_moyenne=Decimal("5.00"),
            nombre_critiques=1,
        )
        self.bonne_note_populaire = Film.objects.create(
            titre="Bonne note populaire",
            synopsis="Film bien note et populaire.",
            genre=self.genre,
            date_sortie=date(2023, 1, 1),
            duree_minutes=118,
            note_moyenne=Decimal("4.50"),
            nombre_critiques=5,
        )
        self.alpha_ex_aequo = Film.objects.create(
            titre="Alpha ex aequo",
            synopsis="Film en egalite.",
            genre=self.genre,
            date_sortie=date(2022, 1, 1),
            duree_minutes=105,
            note_moyenne=Decimal("4.00"),
            nombre_critiques=3,
        )
        self.beta_ex_aequo = Film.objects.create(
            titre="Beta ex aequo",
            synopsis="Autre film en egalite.",
            genre=self.genre,
            date_sortie=date(2021, 1, 1),
            duree_minutes=107,
            note_moyenne=Decimal("4.00"),
            nombre_critiques=3,
        )
        self.plus_populaire = Film.objects.create(
            titre="Plus populaire",
            synopsis="Film avec le plus de critiques.",
            genre=self.genre,
            date_sortie=date(2020, 1, 1),
            duree_minutes=130,
            note_moyenne=Decimal("3.00"),
            nombre_critiques=10,
        )
        self.sans_critique = Film.objects.create(
            titre="Sans critique",
            synopsis="Film sans avis.",
            genre=self.genre,
            date_sortie=date(2019, 1, 1),
            duree_minutes=90,
            note_moyenne=None,
            nombre_critiques=0,
        )
        self.note_sans_critique = Film.objects.create(
            titre="Note incoherente sans critique",
            synopsis="Film sans critique malgre une note stockee.",
            genre=self.genre,
            date_sortie=date(2018, 1, 1),
            duree_minutes=95,
            note_moyenne=Decimal("5.00"),
            nombre_critiques=0,
        )

    def test_ranking_page_displays_both_rankings(self):
        response = self.client.get(reverse("movies:classement"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("films_mieux_notes", response.context)
        self.assertIn("films_populaires", response.context)
        self.assertContains(response, "Films les mieux notés")
        self.assertContains(response, "Films les plus populaires")

    def test_ranking_excludes_films_without_reviews(self):
        response = self.client.get(reverse("movies:classement"))

        films_mieux_notes = list(response.context["films_mieux_notes"])
        films_populaires = list(response.context["films_populaires"])
        self.assertNotIn(self.sans_critique, films_mieux_notes)
        self.assertNotIn(self.sans_critique, films_populaires)
        self.assertNotIn(self.note_sans_critique, films_mieux_notes)
        self.assertNotIn(self.note_sans_critique, films_populaires)

    def test_top_rated_ranking_uses_expected_order(self):
        response = self.client.get(reverse("movies:classement"))

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

    def test_popular_ranking_uses_expected_order(self):
        response = self.client.get(reverse("movies:classement"))

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

    def test_ranking_page_contains_detail_links(self):
        response = self.client.get(reverse("movies:classement"))

        self.assertContains(
            response,
            reverse("movies:film_detail", args=[self.top_note.pk]),
        )


class Phase6HomeViewTests(TestCase):
    def setUp(self):
        self.genre = Genre.objects.create(nom="Science-fiction")
        self.film_populaire = Film.objects.create(
            titre="Film populaire",
            synopsis="Film souvent critique.",
            genre=self.genre,
            date_sortie=date(2024, 5, 1),
            duree_minutes=122,
            note_moyenne=Decimal("4.00"),
            nombre_critiques=7,
        )
        self.film_mieux_note = Film.objects.create(
            titre="Film mieux note",
            synopsis="Film tres bien note.",
            genre=self.genre,
            date_sortie=date(2023, 5, 1),
            duree_minutes=119,
            note_moyenne=Decimal("4.80"),
            nombre_critiques=2,
        )
        self.sans_critique = Film.objects.create(
            titre="Film absent accueil",
            synopsis="Film sans critique.",
            genre=self.genre,
            date_sortie=date(2022, 5, 1),
            duree_minutes=100,
        )

    def test_home_page_displays_entry_points(self):
        response = self.client.get(reverse("movies:accueil"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Explorer le catalogue")
        self.assertContains(response, reverse("movies:films"))
        self.assertContains(response, reverse("movies:classement"))

    def test_home_page_context_contains_ranked_films(self):
        response = self.client.get(reverse("movies:accueil"))

        self.assertIn(self.film_populaire, list(response.context["films_populaires"]))
        self.assertIn(self.film_mieux_note, list(response.context["films_mieux_notes"]))
        self.assertNotIn(self.sans_critique, list(response.context["films_populaires"]))
        self.assertNotIn(self.sans_critique, list(response.context["films_mieux_notes"]))

    def test_home_page_displays_ranked_films_and_detail_links(self):
        response = self.client.get(reverse("movies:accueil"))

        self.assertContains(response, "Film populaire")
        self.assertContains(response, "Film mieux note")
        self.assertContains(
            response,
            reverse("movies:film_detail", args=[self.film_populaire.pk]),
        )

    def test_home_page_displays_empty_states_without_ranked_films(self):
        Film.objects.all().delete()

        response = self.client.get(reverse("movies:accueil"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aucun film populaire pour le moment")
        self.assertContains(response, "Aucun film noté pour le moment")



class MovieListViewTests(TestCase):
    def setUp(self):
        self.genre_action = Genre.objects.create(nom="Action")
        self.genre_drama = Genre.objects.create(nom="Drame")

        self.film_note = Film.objects.create(
            titre="Film noté",
            synopsis="Synopsis 1",
            genre=self.genre_action,
            date_sortie=date(2022, 3, 15),
            duree_minutes=110,
            note_moyenne=Decimal("4.0"),
            nombre_critiques=5,
        )

        self.film_sans_note = Film.objects.create(
            titre="Film sans note",
            synopsis="Synopsis 2",
            genre=self.genre_drama,
            date_sortie=date(2021, 7, 10),
            duree_minutes=95,
            note_moyenne=None,
            nombre_critiques=0,
        )

    def test_films_page_displays_all_films(self):
        response = self.client.get(reverse("movies:films"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Film noté")
        self.assertContains(response, "Film sans note")
        self.assertContains(response, "Catalogue de Films")

    def test_films_page_filters_by_genre_and_note_min(self):
        response = self.client.get(reverse("movies:films"), {"genre": self.genre_action.id, "note_min": "3"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Film noté")
        self.assertNotContains(response, "Film sans note")
        self.assertContains(response, "1 film")


    def test_films_page_filters_by_genre(self):
        response = self.client.get(reverse("movies:films"), {"genre": self.genre_drama.id})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Film noté")
        self.assertContains(response, "Film sans note")

    def test_films_page_filters_by_year(self):
        response = self.client.get(reverse("movies:films"), {"annee": "2022"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Film noté")
        self.assertNotContains(response, "Film sans note")

    def test_films_page_filters_by_note_min(self):
        response = self.client.get(reverse("movies:films"), {"note_min": "4"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Film noté")
        self.assertNotContains(response, "Film sans note")

    def test_films_page_filters_by_combined_criteria(self):
        response = self.client.get(
            reverse("movies:films"),
            {"genre": self.genre_action.id, "annee": "2022", "note_min": "4"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Film noté")
        self.assertNotContains(response, "Film sans note")
        self.assertContains(response, "1 film")

    def test_films_page_ignores_invalid_filters(self):
        response = self.client.get(
            reverse("movies:films"),
            {"genre": "999", "annee": "1900", "note_min": "9"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Film noté")
        self.assertContains(response, "Film sans note")
        self.assertEqual(response.context["selected_genre"], "")
        self.assertEqual(response.context["selected_annee"], "")
        self.assertEqual(response.context["selected_note_min"], "")

    def test_films_page_displays_empty_state(self):
        response = self.client.get(
            reverse("movies:films"),
            {"genre": self.genre_drama.id, "note_min": "4"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Film noté")
        self.assertNotContains(response, "Film sans note")
        self.assertContains(response, "Aucun film ne correspond aux filtres")

    def test_films_page_contains_detail_link(self):
        response = self.client.get(reverse("movies:films"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("movies:film_detail", args=[self.film_note.pk]))


class CommentairePhase5Tests(TestCase):
    """Vérifie l'intégration sécurisée des commentaires dans le détail film."""

    def setUp(self):
        self.auteur_critique = User.objects.create_user(
            username="auteur",
            password="Motdepasse123!",
        )
        self.commentateur = User.objects.create_user(
            username="commentateur",
            password="Motdepasse123!",
        )
        self.autre_utilisateur = User.objects.create_user(
            username="autre",
            password="Motdepasse123!",
        )
        genre = Genre.objects.create(nom="Science-fiction")
        self.film = Film.objects.create(
            titre="Voyage orbital",
            synopsis="Une aventure spatiale.",
            genre=genre,
            date_sortie=date(2024, 8, 2),
            duree_minutes=124,
        )
        self.critique = Critique.objects.create(
            film=self.film,
            utilisateur=self.auteur_critique,
            titre="Très réussi",
            texte="Une critique de référence.",
            note=4,
        )
        self.commentaire_existant = Commentaire.objects.create(
            critique=self.critique,
            utilisateur=self.autre_utilisateur,
            texte="Je partage cet avis.",
        )
        self.detail_url = reverse("movies:film_detail", args=[self.film.pk])
        self.add_url = reverse("movies:ajouter_commentaire", args=[self.critique.pk])

    def test_anonymous_user_can_read_existing_comments(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Très réussi")
        self.assertContains(response, "Je partage cet avis.")
        self.assertContains(response, "autre")

    def test_anonymous_user_does_not_see_comment_form(self):
        response = self.client.get(self.detail_url)

        self.assertNotContains(response, self.add_url)
        self.assertNotContains(response, "Publier le commentaire")
        self.assertContains(response, "Connectez-vous")
        self.assertContains(response, f"%23critique-{self.critique.pk}")

    def test_anonymous_user_cannot_publish_comment(self):
        response = self.client.post(self.add_url, {"texte": "Tentative anonyme"})

        self.assertRedirects(
            response,
            f"{reverse('accounts:connexion')}?next={self.add_url}",
        )
        self.assertFalse(
            Commentaire.objects.filter(texte="Tentative anonyme").exists()
        )

    def test_authenticated_user_sees_comment_form_with_unique_field_id(self):
        self.client.force_login(self.commentateur)

        response = self.client.get(self.detail_url)

        self.assertContains(response, self.add_url)
        self.assertContains(response, "Publier le commentaire")
        self.assertContains(response, f'id="id_texte_{self.critique.pk}"')

    def test_authenticated_user_can_publish_valid_comment(self):
        self.client.force_login(self.commentateur)

        response = self.client.post(self.add_url, {"texte": "Excellent point de vue."})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Commentaire.objects.filter(texte="Excellent point de vue.").exists()
        )

    def test_new_comment_is_associated_with_target_critique(self):
        self.client.force_login(self.commentateur)

        self.client.post(self.add_url, {"texte": "Sur cette critique."})

        commentaire = Commentaire.objects.get(texte="Sur cette critique.")
        self.assertEqual(commentaire.critique, self.critique)

    def test_new_comment_is_associated_with_logged_in_user(self):
        self.client.force_login(self.commentateur)

        self.client.post(self.add_url, {"texte": "Mon commentaire."})

        commentaire = Commentaire.objects.get(texte="Mon commentaire.")
        self.assertEqual(commentaire.utilisateur, self.commentateur)

    def test_forged_user_and_critique_post_values_are_ignored(self):
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

        commentaire = Commentaire.objects.get(texte="Associations protégées.")
        self.assertEqual(commentaire.utilisateur, self.commentateur)
        self.assertEqual(commentaire.critique, self.critique)

    def test_blank_or_whitespace_only_comment_is_rejected(self):
        self.client.force_login(self.commentateur)
        initial_count = Commentaire.objects.count()

        response = self.client.post(self.add_url, {"texte": "   \n  "})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Le commentaire ne peut pas être vide.")
        self.assertEqual(Commentaire.objects.count(), initial_count)

    def test_unknown_critique_returns_404(self):
        self.client.force_login(self.commentateur)

        response = self.client.post(
            reverse("movies:ajouter_commentaire", args=[999999]),
            {"texte": "Introuvable"},
        )

        self.assertEqual(response.status_code, 404)

    def test_success_redirect_returns_to_target_critique_anchor(self):
        self.client.force_login(self.commentateur)

        response = self.client.post(self.add_url, {"texte": "Retour ciblé."})

        self.assertEqual(
            response["Location"],
            f"{self.detail_url}#critique-{self.critique.pk}",
        )

    def test_login_form_preserves_next_target(self):
        next_target = f"{self.detail_url}#critique-{self.critique.pk}"

        response = self.client.get(
            reverse("accounts:connexion"),
            {"next": next_target},
        )

        self.assertContains(response, 'name="next"')
        self.assertContains(response, f'value="{next_target}"')
