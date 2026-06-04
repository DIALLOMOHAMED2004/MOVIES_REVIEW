from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from movies.models import Acteur, Casting, Commentaire, Critique, Film, Genre


class DashboardAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="password",
            is_staff=True,
        )
        self.user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="password",
        )
        self.superuser = User.objects.create_user(
            username="superuser",
            email="superuser@example.com",
            password="password",
            is_staff=False,
            is_superuser=True,
        )

    def test_anonymous_user_is_redirected_from_dashboard(self):
        response = self.client.get(reverse("dashboard:home"))

        self.assertRedirects(
            response,
            f"{reverse('accounts:connexion')}?next={reverse('dashboard:home')}",
        )

    def test_normal_user_cannot_access_dashboard(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard:home"))

        self.assertEqual(response.status_code, 403)

    def test_staff_user_can_access_dashboard(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard administrateur")

    def test_superuser_can_access_dashboard_and_see_link(self):
        self.client.force_login(self.superuser)

        dashboard_response = self.client.get(reverse("dashboard:home"))
        home_response = self.client.get(reverse("movies:accueil"))

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(home_response, reverse("dashboard:home"))
        self.assertContains(home_response, "Dashboard")

    def test_normal_user_cannot_access_sensitive_dashboard_url(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard:film_create"))

        self.assertEqual(response.status_code, 403)

    def test_dashboard_link_is_visible_for_staff_user(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("movies:accueil"))

        self.assertContains(response, reverse("dashboard:home"))
        self.assertContains(response, "Dashboard")

    def test_dashboard_link_is_absent_for_normal_user(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("movies:accueil"))

        self.assertNotContains(response, reverse("dashboard:home"))
        self.assertNotContains(response, "Dashboard")


class DashboardFunctionalTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="password",
            is_staff=True,
        )
        self.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password",
        )
        self.genre = Genre.objects.create(nom="Drame")
        self.actor = Acteur.objects.create(nom="Camille Durand")
        self.film = Film.objects.create(
            titre="Nuit rouge",
            synopsis="Une enquête nocturne.",
            genre=self.genre,
            date_sortie="2024-01-10",
            duree_minutes=120,
        )
        Casting.objects.create(film=self.film, acteur=self.actor)
        self.critique = Critique.objects.create(
            film=self.film,
            utilisateur=self.user,
            titre="Très réussi",
            texte="Une critique complète.",
            note=4,
        )
        self.commentaire = Commentaire.objects.create(
            critique=self.critique,
            utilisateur=self.user,
            texte="Je partage cet avis.",
        )
        self.client.force_login(self.staff)

    def test_review_list_displays_film_author_and_note_selects(self):
        response = self.client.get(reverse("dashboard:critique_list"))

        self.assertContains(
            response,
            '<select id="film" name="film" class="form-control">',
        )
        self.assertContains(
            response,
            '<select id="auteur" name="auteur" class="form-control">',
        )
        self.assertContains(
            response,
            '<select id="note" name="note" class="form-control">',
        )
        self.assertContains(response, "Tous les films")
        self.assertContains(response, "Tous les auteurs")

    def test_review_list_filters_by_selected_movie(self):
        other_film = Film.objects.create(
            titre="Aube froide",
            synopsis="Un autre film.",
            genre=self.genre,
            date_sortie="2025-02-01",
            duree_minutes=98,
        )
        Critique.objects.create(
            film=other_film,
            utilisateur=self.user,
            titre="Avis sur Aube froide",
            texte="Une autre critique.",
            note=3,
        )

        response = self.client.get(
            reverse("dashboard:critique_list"),
            {"film": str(self.film.pk)},
        )

        self.assertEqual(list(response.context["critiques"]), [self.critique])
        self.assertContains(
            response,
            f'<option value="{self.film.pk}" selected>',
        )

    def test_review_list_filters_by_selected_author(self):
        User = get_user_model()
        other_user = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="password",
        )
        Critique.objects.create(
            film=self.film,
            utilisateur=other_user,
            titre="Un autre avis",
            texte="Une autre critique.",
            note=2,
        )

        response = self.client.get(
            reverse("dashboard:critique_list"),
            {"auteur": str(self.user.pk)},
        )

        self.assertEqual(list(response.context["critiques"]), [self.critique])
        self.assertContains(
            response,
            f'<option value="{self.user.pk}" selected>',
        )

    def test_review_list_filters_by_selected_note(self):
        User = get_user_model()
        other_user = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="password",
        )
        Critique.objects.create(
            film=self.film,
            utilisateur=other_user,
            titre="Un autre avis",
            texte="Une autre critique.",
            note=2,
        )

        response = self.client.get(
            reverse("dashboard:critique_list"),
            {"note": "4"},
        )

        self.assertEqual(list(response.context["critiques"]), [self.critique])
        self.assertContains(response, '<option value="4" selected>')

    def test_review_list_ignores_invalid_filter_values(self):
        User = get_user_model()
        other_user = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="password",
        )
        other_review = Critique.objects.create(
            film=self.film,
            utilisateur=other_user,
            titre="Un autre avis",
            texte="Une autre critique.",
            note=2,
        )

        response = self.client.get(
            reverse("dashboard:critique_list"),
            {"film": "invalide", "auteur": "-1", "note": "9"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.context["critiques"]),
            {self.critique, other_review},
        )

    def test_staff_can_add_movie_and_sync_casting(self):
        response = self.client.post(
            reverse("dashboard:film_create"),
            {
                "titre": "Aube froide",
                "synopsis": "Un nouveau film.",
                "genre": self.genre.pk,
                "date_sortie": "2025-02-01",
                "duree_minutes": 98,
                "acteurs": [self.actor.pk],
            },
        )

        self.assertRedirects(response, reverse("dashboard:film_list"))
        film = Film.objects.get(titre="Aube froide")
        self.assertEqual(film.note_moyenne, None)
        self.assertEqual(film.nombre_critiques, 0)
        self.assertTrue(Casting.objects.filter(film=film, acteur=self.actor).exists())

    def test_staff_can_update_movie_and_sync_casting(self):
        other_actor = Acteur.objects.create(nom="Louis Martin")

        response = self.client.post(
            reverse("dashboard:film_update", args=[self.film.pk]),
            {
                "titre": "Nuit rouge restaurée",
                "synopsis": self.film.synopsis,
                "genre": self.genre.pk,
                "date_sortie": "2024-01-10",
                "duree_minutes": 121,
                "acteurs": [other_actor.pk],
            },
        )

        self.assertRedirects(response, reverse("dashboard:film_list"))
        self.film.refresh_from_db()
        self.assertEqual(self.film.titre, "Nuit rouge restaurée")
        self.assertFalse(
            Casting.objects.filter(film=self.film, acteur=self.actor).exists()
        )
        self.assertTrue(
            Casting.objects.filter(film=self.film, acteur=other_actor).exists()
        )

    def test_staff_can_delete_movie(self):
        response = self.client.post(reverse("dashboard:film_delete", args=[self.film.pk]))

        self.assertRedirects(response, reverse("dashboard:film_list"))
        self.assertFalse(Film.objects.filter(pk=self.film.pk).exists())
        self.assertFalse(Critique.objects.filter(pk=self.critique.pk).exists())
        self.assertFalse(Commentaire.objects.filter(pk=self.commentaire.pk).exists())

    def test_used_genre_cannot_be_deleted(self):
        response = self.client.post(
            reverse("dashboard:genre_delete", args=[self.genre.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse("dashboard:genre_list"))
        self.assertTrue(Genre.objects.filter(pk=self.genre.pk).exists())
        self.assertContains(
            response,
            "Ce genre est encore utilisé par un ou plusieurs films.",
        )

    def test_actor_used_in_casting_cannot_be_deleted(self):
        response = self.client.post(
            reverse("dashboard:acteur_delete", args=[self.actor.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse("dashboard:acteur_list"))
        self.assertTrue(Acteur.objects.filter(pk=self.actor.pk).exists())
        self.assertContains(
            response,
            "Cet acteur est encore associé à un ou plusieurs films.",
        )

    def test_staff_can_delete_review(self):
        response = self.client.post(
            reverse("dashboard:critique_delete", args=[self.critique.pk])
        )

        self.assertRedirects(response, reverse("dashboard:critique_list"))
        self.assertFalse(Critique.objects.filter(pk=self.critique.pk).exists())

    def test_review_delete_confirmation_get_does_not_delete(self):
        response = self.client.get(
            reverse("dashboard:critique_delete", args=[self.critique.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Critique.objects.filter(pk=self.critique.pk).exists())
        self.assertContains(response, "Supprimer la critique")

    def test_review_delete_updates_movie_statistics(self):
        self.assertEqual(self.film.nombre_critiques, 1)
        self.assertEqual(self.film.note_moyenne, 4)

        self.client.post(reverse("dashboard:critique_delete", args=[self.critique.pk]))

        self.film.refresh_from_db()
        self.assertEqual(self.film.nombre_critiques, 0)
        self.assertIsNone(self.film.note_moyenne)

    def test_comment_delete_confirmation_get_does_not_delete(self):
        response = self.client.get(
            reverse("dashboard:commentaire_delete", args=[self.commentaire.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Commentaire.objects.filter(pk=self.commentaire.pk).exists())
        self.assertContains(response, "Supprimer le commentaire")

    def test_staff_can_delete_comment_with_post(self):
        response = self.client.post(
            reverse("dashboard:commentaire_delete", args=[self.commentaire.pk])
        )

        self.assertRedirects(response, reverse("dashboard:commentaire_list"))
        self.assertFalse(Commentaire.objects.filter(pk=self.commentaire.pk).exists())

    def test_dashboard_home_displays_statistics(self):
        response = self.client.get(reverse("dashboard:home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["nombre_films"], 1)
        self.assertEqual(response.context["nombre_critiques"], 1)
        self.assertEqual(response.context["nombre_commentaires"], 1)
        self.assertEqual(response.context["nombre_utilisateurs"], 2)
        self.assertContains(response, "Nuit rouge")
        self.assertContains(response, "Je partage cet avis.")
