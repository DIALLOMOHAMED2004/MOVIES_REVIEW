import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


User = get_user_model()


@override_settings(
    PASSWORD_HASHERS=[
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ],
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="no-reply@movie-review.local",
)
class AccountsAuthTests(TestCase):
    """Vérifie les flux principaux de la phase utilisateurs."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="cinephile",
            email="cinephile@example.com",
            password="Motdepasse123!",
        )

    def test_registration_redirects_to_login_without_logging_user_in(self):
        response = self.client.post(
            reverse("accounts:inscription"),
            {
                "username": "nouveau",
                "email": "nouveau@example.com",
                "password1": "Motdepasse123!",
                "password2": "Motdepasse123!",
            },
            follow=True,
        )

        new_user = User.objects.get(username="nouveau")
        self.assertRedirects(response, reverse("accounts:connexion"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(
            response,
            "Votre compte a été créé avec succès. Vous pouvez maintenant vous connecter.",
        )
        self.assertEqual(new_user.email, "nouveau@example.com")

    def test_registration_rejects_duplicate_email(self):
        response = self.client.post(
            reverse("accounts:inscription"),
            {
                "username": "autre",
                "email": "cinephile@example.com",
                "password1": "Motdepasse123!",
                "password2": "Motdepasse123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "email",
            "Cette adresse email est déjà utilisée.",
        )

    def test_login_with_username(self):
        response = self.client.post(
            reverse("accounts:connexion"),
            {
                "username": "cinephile",
                "password": "Motdepasse123!",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("accounts:profil"))
        self.assertEqual(str(self.user.pk), self.client.session["_auth_user_id"])

    def test_login_with_email(self):
        response = self.client.post(
            reverse("accounts:connexion"),
            {
                "username": "cinephile@example.com",
                "password": "Motdepasse123!",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("accounts:profil"))
        self.assertEqual(str(self.user.pk), self.client.session["_auth_user_id"])

    def test_login_rejects_wrong_password(self):
        response = self.client.post(
            reverse("accounts:connexion"),
            {
                "username": "cinephile",
                "password": "mauvais",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_password_reset_request_page_is_accessible(self):
        response = self.client.get(reverse("accounts:password_reset"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mot de passe oublié")

    def test_login_page_contains_password_reset_link(self):
        response = self.client.get(reverse("accounts:connexion"))

        self.assertContains(response, "Mot de passe oublié ?")
        self.assertContains(response, reverse("accounts:password_reset"))

    def test_password_reset_request_sends_email_and_redirects(self):
        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": "cinephile@example.com"},
        )

        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Movie Review", mail.outbox[0].subject)

    def test_password_reset_email_contains_namespaced_confirm_url(self):
        email = self._request_password_reset_email()

        self.assertRegex(
            email.body,
            r"http://testserver/reset/[^/]+/[^/]+/",
        )

    def test_password_reset_confirm_changes_password_without_logging_user_in(self):
        confirm_url = self._get_valid_password_reset_form_url()

        response = self.client.post(
            confirm_url,
            {
                "new_password1": "ResetMotdepasse123!",
                "new_password2": "ResetMotdepasse123!",
            },
        )

        self.assertRedirects(response, reverse("accounts:password_reset_complete"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("ResetMotdepasse123!"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_user_can_login_with_new_password_after_password_reset(self):
        confirm_url = self._get_valid_password_reset_form_url()
        self.client.post(
            confirm_url,
            {
                "new_password1": "ResetMotdepasse123!",
                "new_password2": "ResetMotdepasse123!",
            },
        )

        response = self.client.post(
            reverse("accounts:connexion"),
            {
                "username": "cinephile@example.com",
                "password": "ResetMotdepasse123!",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("accounts:profil"))
        self.assertEqual(str(self.user.pk), self.client.session["_auth_user_id"])

    def test_password_reset_complete_page_links_to_login(self):
        response = self.client.get(reverse("accounts:password_reset_complete"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Se connecter")
        self.assertContains(response, reverse("accounts:connexion"))

    def test_logout_requires_post_and_clears_session(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("accounts:deconnexion"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("movies:accueil"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_anonymous_user_is_redirected_from_profile(self):
        response = self.client.get(reverse("accounts:profil"))

        self.assertRedirects(
            response,
            f"{reverse('accounts:connexion')}?next={reverse('accounts:profil')}",
        )

    def test_profile_update_changes_username_and_email(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:modifier_profil"),
            {
                "username": "cinephile_modifie",
                "email": "modifie@example.com",
                "old_password": "",
                "new_password1": "",
                "new_password2": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "cinephile_modifie")
        self.assertEqual(self.user.email, "modifie@example.com")

    def test_password_change_updates_password_and_keeps_user_logged_in(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:modifier_profil"),
            {
                "username": "cinephile",
                "email": "cinephile@example.com",
                "old_password": "Motdepasse123!",
                "new_password1": "NouveauMotdepasse123!",
                "new_password2": "NouveauMotdepasse123!",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NouveauMotdepasse123!"))

        profile_response = self.client.get(reverse("accounts:profil"))
        self.assertEqual(profile_response.status_code, 200)

    def test_navbar_changes_with_authentication_state(self):
        anonymous_response = self.client.get(reverse("accounts:connexion"))
        self.assertContains(anonymous_response, "Connexion")
        self.assertContains(anonymous_response, "Inscription")
        self.assertNotContains(anonymous_response, "Déconnexion")

        self.client.force_login(self.user)
        authenticated_response = self.client.get(reverse("accounts:profil"))
        self.assertContains(authenticated_response, "Profil")
        self.assertContains(authenticated_response, "Déconnexion")
        self.assertNotContains(authenticated_response, "Inscription")

    def _request_password_reset_email(self):
        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": self.user.email},
        )
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        return mail.outbox[0]

    def _get_valid_password_reset_form_url(self):
        email = self._request_password_reset_email()
        match = re.search(
            r"http://testserver(?P<path>/reset/[^/]+/[^/]+/)",
            email.body,
        )
        self.assertIsNotNone(match)

        response = self.client.get(match.group("path"))
        self.assertEqual(response.status_code, 302)
        return response["Location"]
