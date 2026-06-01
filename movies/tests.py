from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Commentaire, Critique, Film, Genre


User = get_user_model()



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
