import re
from datetime import date

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from movies.models import Critique, Film, Genre


# Récupère le modèle utilisateur actif du projet.
# Cela rend les tests compatibles avec le User standard de Django
# ou avec un éventuel modèle utilisateur personnalisé.
User = get_user_model()


# override_settings permet de modifier temporairement certains réglages Django
# uniquement pendant l'exécution de cette classe de tests.
@override_settings(
    # Utilise un algorithme de hash rapide pour accélérer les tests.
    # MD5PasswordHasher ne doit pas être utilisé en production,
    # mais il est pratique ici car les tests créent et vérifient des mots de passe.
    PASSWORD_HASHERS=[
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ],

    # Utilise le backend email en mémoire.
    # Les emails ne sont pas réellement envoyés : ils sont stockés dans mail.outbox.
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",

    # Adresse d'expéditeur utilisée dans les emails générés pendant les tests.
    DEFAULT_FROM_EMAIL="no-reply@movie-review.local",
)
class AccountsAuthTests(TestCase):
    """Vérifie les flux principaux de la phase utilisateurs."""

    def setUp(self):
        # Méthode exécutée avant chaque test.
        # Elle crée un utilisateur de référence utilisé par la majorité des scénarios.
        self.user = User.objects.create_user(
            username="cinephile",
            email="cinephile@example.com",
            password="Motdepasse123!",
        )

    def test_registration_redirects_to_login_without_logging_user_in(self):
        # Vérifie qu'une inscription réussie :
        # - crée bien un nouvel utilisateur ;
        # - redirige vers la page de connexion ;
        # - ne connecte pas automatiquement l'utilisateur ;
        # - affiche un message de succès.
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

        # Vérifie que l'utilisateur a bien été créé en base.
        new_user = User.objects.get(username="nouveau")

        # Vérifie que la réponse finale correspond bien à la page de connexion.
        self.assertRedirects(response, reverse("accounts:connexion"))

        # Vérifie que l'inscription ne connecte pas automatiquement l'utilisateur.
        self.assertNotIn("_auth_user_id", self.client.session)

        # Vérifie que le message de succès est affiché à l'utilisateur.
        self.assertContains(
            response,
            "Votre compte a été créé avec succès. Vous pouvez maintenant vous connecter.",
        )

        # Vérifie que l'email enregistré correspond bien à celui envoyé.
        self.assertEqual(new_user.email, "nouveau@example.com")

    def test_registration_rejects_duplicate_email(self):
        # Vérifie qu'une inscription avec un email déjà utilisé est refusée.
        response = self.client.post(
            reverse("accounts:inscription"),
            {
                "username": "autre",
                "email": "cinephile@example.com",
                "password1": "Motdepasse123!",
                "password2": "Motdepasse123!",
            },
        )

        # Le formulaire invalide doit être réaffiché avec un status HTTP 200.
        self.assertEqual(response.status_code, 200)

        # Vérifie que l'erreur attendue est bien attachée au champ email.
        self.assertFormError(
            response.context["form"],
            "email",
            "Cette adresse email est déjà utilisée.",
        )

    def test_login_with_username(self):
        # Vérifie qu'un utilisateur peut se connecter avec son nom d'utilisateur.
        response = self.client.post(
            reverse("accounts:connexion"),
            {
                "username": "cinephile",
                "password": "Motdepasse123!",
            },
        )

        # Une connexion réussie doit rediriger l'utilisateur.
        self.assertEqual(response.status_code, 302)

        # Vérifie que la destination est bien la page de profil.
        self.assertEqual(response["Location"], reverse("accounts:profil"))

        # Vérifie que l'utilisateur connecté est bien stocké dans la session.
        self.assertEqual(str(self.user.pk), self.client.session["_auth_user_id"])

    def test_login_with_email(self):
        # Vérifie qu'un utilisateur peut aussi se connecter avec son adresse email.
        response = self.client.post(
            reverse("accounts:connexion"),
            {
                "username": "cinephile@example.com",
                "password": "Motdepasse123!",
            },
        )

        # Une connexion réussie doit produire une redirection HTTP.
        self.assertEqual(response.status_code, 302)

        # Vérifie que l'utilisateur est envoyé vers son profil.
        self.assertEqual(response["Location"], reverse("accounts:profil"))

        # Vérifie que la session contient bien l'identifiant de l'utilisateur connecté.
        self.assertEqual(str(self.user.pk), self.client.session["_auth_user_id"])

    def test_login_rejects_wrong_password(self):
        # Vérifie qu'un mauvais mot de passe empêche la connexion.
        response = self.client.post(
            reverse("accounts:connexion"),
            {
                "username": "cinephile",
                "password": "mauvais",
            },
        )

        # Le formulaire doit être réaffiché.
        self.assertEqual(response.status_code, 200)

        # Aucun utilisateur ne doit être connecté en session.
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_password_reset_request_page_is_accessible(self):
        # Vérifie que la page de demande de réinitialisation est accessible.
        response = self.client.get(reverse("accounts:password_reset"))

        # La page doit répondre correctement.
        self.assertEqual(response.status_code, 200)

        # Vérifie qu'un texte attendu est bien présent dans le rendu HTML.
        self.assertContains(response, "Mot de passe oublié")

    def test_login_page_contains_password_reset_link(self):
        # Vérifie que la page de connexion contient un lien vers
        # la fonctionnalité de mot de passe oublié.
        response = self.client.get(reverse("accounts:connexion"))

        # Vérifie le texte du lien.
        self.assertContains(response, "Mot de passe oublié ?")

        # Vérifie l'URL du lien.
        self.assertContains(response, reverse("accounts:password_reset"))

    def test_password_reset_request_sends_email_and_redirects(self):
        # Vérifie qu'une demande de réinitialisation valide :
        # - redirige vers la page de confirmation ;
        # - génère exactement un email ;
        # - utilise un sujet cohérent avec le projet.
        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": "cinephile@example.com"},
        )

        # Vérifie la redirection après soumission.
        self.assertRedirects(response, reverse("accounts:password_reset_done"))

        # Vérifie qu'un email a été généré dans la boîte mémoire de test.
        self.assertEqual(len(mail.outbox), 1)

        # Vérifie que le sujet de l'email contient le nom du projet.
        self.assertIn("Movie Review", mail.outbox[0].subject)

    def test_password_reset_email_contains_namespaced_confirm_url(self):
        # Vérifie que l'email de réinitialisation contient une URL de confirmation valide.
        email = self._request_password_reset_email()

        # Vérifie que le corps de l'email contient une URL du type :
        # http://testserver/reset/<uid>/<token>/
        self.assertRegex(
            email.body,
            r"http://testserver/reset/[^/]+/[^/]+/",
        )

    def test_password_reset_confirm_changes_password_without_logging_user_in(self):
        # Vérifie qu'un lien valide de réinitialisation permet de modifier le mot de passe
        # sans connecter automatiquement l'utilisateur.
        confirm_url = self._get_valid_password_reset_form_url()

        # Soumet le nouveau mot de passe via le formulaire de confirmation.
        response = self.client.post(
            confirm_url,
            {
                "new_password1": "ResetMotdepasse123!",
                "new_password2": "ResetMotdepasse123!",
            },
        )

        # Vérifie que l'utilisateur est redirigé vers la page de fin de réinitialisation.
        self.assertRedirects(response, reverse("accounts:password_reset_complete"))

        # Recharge l'utilisateur depuis la base de données.
        self.user.refresh_from_db()

        # Vérifie que le nouveau mot de passe est bien enregistré.
        self.assertTrue(self.user.check_password("ResetMotdepasse123!"))

        # Vérifie que l'utilisateur n'a pas été connecté automatiquement.
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_user_can_login_with_new_password_after_password_reset(self):
        # Vérifie qu'après réinitialisation, l'utilisateur peut se connecter
        # avec son nouveau mot de passe.
        confirm_url = self._get_valid_password_reset_form_url()

        # Change le mot de passe via le lien de réinitialisation.
        self.client.post(
            confirm_url,
            {
                "new_password1": "ResetMotdepasse123!",
                "new_password2": "ResetMotdepasse123!",
            },
        )

        # Tente une connexion avec l'email et le nouveau mot de passe.
        response = self.client.post(
            reverse("accounts:connexion"),
            {
                "username": "cinephile@example.com",
                "password": "ResetMotdepasse123!",
            },
        )

        # Vérifie que la connexion réussit.
        self.assertEqual(response.status_code, 302)

        # Vérifie que l'utilisateur est redirigé vers son profil.
        self.assertEqual(response["Location"], reverse("accounts:profil"))

        # Vérifie que la session correspond bien à l'utilisateur attendu.
        self.assertEqual(str(self.user.pk), self.client.session["_auth_user_id"])

    def test_password_reset_complete_page_links_to_login(self):
        # Vérifie que la page finale de réinitialisation contient un lien
        # permettant à l'utilisateur de revenir à la connexion.
        response = self.client.get(reverse("accounts:password_reset_complete"))

        # Vérifie que la page est accessible.
        self.assertEqual(response.status_code, 200)

        # Vérifie que le texte du lien de connexion est présent.
        self.assertContains(response, "Se connecter")

        # Vérifie que l'URL de connexion est présente.
        self.assertContains(response, reverse("accounts:connexion"))

    def test_logout_requires_post_and_clears_session(self):
        # Connecte artificiellement l'utilisateur pour tester la déconnexion.
        self.client.force_login(self.user)

        # Envoie une requête POST vers la route de déconnexion.
        response = self.client.post(reverse("accounts:deconnexion"))

        # Vérifie que la déconnexion redirige l'utilisateur.
        self.assertEqual(response.status_code, 302)

        # Vérifie que la redirection mène vers la page d'accueil des films.
        self.assertEqual(response["Location"], reverse("movies:accueil"))

        # Vérifie que l'utilisateur n'est plus stocké en session.
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_anonymous_user_is_redirected_from_profile(self):
        # Vérifie qu'un utilisateur non connecté ne peut pas accéder au profil.
        response = self.client.get(reverse("accounts:profil"))

        # Vérifie la redirection vers la page de connexion avec le paramètre next.
        self.assertRedirects(
            response,
            f"{reverse('accounts:connexion')}?next={reverse('accounts:profil')}",
        )

    def test_profile_update_changes_username_and_email(self):
        # Connecte l'utilisateur pour pouvoir modifier son profil.
        self.client.force_login(self.user)

        # Soumet une modification du username et de l'email.
        # Les champs liés au mot de passe sont envoyés vides pour indiquer
        # qu'on ne souhaite pas modifier le mot de passe dans ce scénario.
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

        # Vérifie que la modification redirige après succès.
        self.assertEqual(response.status_code, 302)

        # Recharge l'utilisateur depuis la base.
        self.user.refresh_from_db()

        # Vérifie que le username a été modifié.
        self.assertEqual(self.user.username, "cinephile_modifie")

        # Vérifie que l'email a été modifié.
        self.assertEqual(self.user.email, "modifie@example.com")

    def test_password_change_updates_password_and_keeps_user_logged_in(self):
        # Connecte l'utilisateur pour tester le changement de mot de passe
        # depuis la page de modification du profil.
        self.client.force_login(self.user)

        # Soumet le formulaire avec l'ancien mot de passe et le nouveau.
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

        # Vérifie que la modification redirige après succès.
        self.assertEqual(response.status_code, 302)

        # Recharge l'utilisateur depuis la base.
        self.user.refresh_from_db()

        # Vérifie que le mot de passe a bien changé.
        self.assertTrue(self.user.check_password("NouveauMotdepasse123!"))

        # Vérifie que l'utilisateur reste connecté après le changement de mot de passe.
        profile_response = self.client.get(reverse("accounts:profil"))
        self.assertEqual(profile_response.status_code, 200)

    def test_navbar_changes_with_authentication_state(self):
        # Vérifie que la barre de navigation change selon que l'utilisateur
        # est connecté ou non.

        # Cas 1 : utilisateur anonyme.
        anonymous_response = self.client.get(reverse("accounts:connexion"))

        # La navbar doit afficher Connexion et Inscription.
        self.assertContains(anonymous_response, "Connexion")
        self.assertContains(anonymous_response, "Inscription")

        # La navbar ne doit pas afficher Déconnexion.
        self.assertNotContains(anonymous_response, "Déconnexion")

        # Cas 2 : utilisateur connecté.
        self.client.force_login(self.user)
        authenticated_response = self.client.get(reverse("accounts:profil"))

        # La navbar doit afficher Profil et Déconnexion.
        self.assertContains(authenticated_response, "Profil")
        self.assertContains(authenticated_response, "Déconnexion")

        # La navbar ne doit plus afficher Inscription.
        self.assertNotContains(authenticated_response, "Inscription")

    def test_profile_displays_real_user_reviews_and_actions(self):
        # Vérifie que la page profil affiche les vraies critiques de l'utilisateur
        # ainsi que les actions de modification et de suppression associées.

        # Crée un genre nécessaire à la création d'un film.
        genre = Genre.objects.create(nom="Profil")

        # Crée un film de test lié au genre.
        film = Film.objects.create(
            titre="Film du profil",
            synopsis="Film utilisé pour vérifier la liste des critiques.",
            genre=genre,
            date_sortie=date(2026, 2, 5),
            duree_minutes=110,
        )

        # Crée une critique associée à l'utilisateur de test.
        critique = Critique.objects.create(
            film=film,
            utilisateur=self.user,
            titre="Ma critique visible",
            texte="Cette critique doit apparaître dans le profil utilisateur.",
            note=5,
        )

        # Connecte l'utilisateur pour accéder à son profil.
        self.client.force_login(self.user)

        # Charge la page profil.
        response = self.client.get(reverse("accounts:profil"))

        # Vérifie que la page répond correctement.
        self.assertEqual(response.status_code, 200)

        # Vérifie que la critique créée est bien transmise au template.
        self.assertEqual(response.context["reviews"], [critique])

        # Vérifie que le compteur de critiques vaut 1.
        self.assertEqual(response.context["review_count"], 1)

        # Vérifie que le titre de la critique apparaît dans la page.
        self.assertContains(response, "Ma critique visible")

        # Vérifie que le titre du film apparaît également.
        self.assertContains(response, "Film du profil")

        # Vérifie que le lien de modification de la critique est présent.
        self.assertContains(response, reverse("movies:review_update", args=[critique.pk]))

        # Vérifie que le lien de suppression de la critique est présent.
        self.assertContains(response, reverse("movies:review_delete", args=[critique.pk]))

        # Comme une critique existe, le message d'état vide ne doit pas apparaître.
        self.assertNotContains(response, "Aucune critique publiée")

    def _request_password_reset_email(self):
        # Méthode utilitaire interne aux tests.
        # Elle déclenche une demande de réinitialisation de mot de passe
        # pour l'utilisateur de référence.
        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": self.user.email},
        )

        # Vérifie que la demande redirige vers la page indiquant
        # que l'email de réinitialisation a été envoyé.
        self.assertRedirects(response, reverse("accounts:password_reset_done"))

        # Vérifie qu'un seul email a été généré.
        self.assertEqual(len(mail.outbox), 1)

        # Retourne l'email généré pour permettre aux tests de l'inspecter.
        return mail.outbox[0]

    def _get_valid_password_reset_form_url(self):
        # Méthode utilitaire interne aux tests.
        # Elle récupère une URL valide de formulaire de réinitialisation
        # à partir du contenu de l'email envoyé.
        email = self._request_password_reset_email()

        # Recherche dans le corps de l'email une URL de confirmation.
        # Le groupe nommé "path" extrait uniquement la partie chemin de l'URL,
        # par exemple : /reset/<uid>/<token>/
        match = re.search(
            r"http://testserver(?P<path>/reset/[^/]+/[^/]+/)",
            email.body,
        )

        # Vérifie qu'une URL a bien été trouvée.
        self.assertIsNotNone(match)

        # Django redirige souvent l'URL brute contenant le token vers une URL
        # interne sécurisée où le token est remplacé par "set-password".
        response = self.client.get(match.group("path"))

        # Vérifie que cette première URL produit bien une redirection.
        self.assertEqual(response.status_code, 302)

        # Retourne l'URL finale du formulaire de changement de mot de passe.
        return response["Location"]