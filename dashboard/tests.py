from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from movies.models import Acteur, Casting, Commentaire, Critique, Film, Genre


class DashboardAccessTests(TestCase):
    # Cette classe regroupe les tests liés aux droits d'accès du dashboard.
    #
    # Elle vérifie principalement trois profils d'utilisateurs :
    # - utilisateur anonyme ;
    # - utilisateur connecté simple ;
    # - utilisateur staff ;
    # - superuser.
    #
    # L'objectif est de s'assurer que le dashboard personnalisé reste protégé
    # et qu'il n'est accessible qu'aux utilisateurs autorisés.

    def setUp(self):
        # setUp est exécutée avant chaque test de cette classe.
        #
        # Elle prépare les utilisateurs nécessaires aux différents scénarios
        # afin d'éviter de répéter leur création dans chaque méthode de test.

        # Récupère le modèle utilisateur actif du projet.
        # Cela permet de rester compatible avec un User Django standard
        # ou avec un modèle utilisateur personnalisé.
        User = get_user_model()

        # Crée un utilisateur staff.
        #
        # is_staff=True signifie que cet utilisateur doit pouvoir accéder
        # au dashboard administrateur personnalisé.
        self.staff = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="password",
            is_staff=True,
        )

        # Crée un utilisateur normal.
        #
        # Cet utilisateur est connecté mais ne possède pas de privilèges staff.
        # Il doit donc recevoir une erreur 403 lorsqu'il tente d'accéder au dashboard.
        self.user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="password",
        )

        # Crée un superuser.
        #
        # Ici, is_staff=False mais is_superuser=True.
        # Ce test permet de vérifier que le dashboard accepte aussi les superusers,
        # même lorsqu'ils ne sont pas marqués explicitement comme staff.
        self.superuser = User.objects.create_user(
            username="superuser",
            email="superuser@example.com",
            password="password",
            is_staff=False,
            is_superuser=True,
        )

    def test_anonymous_user_is_redirected_from_dashboard(self):
        # Vérifie qu'un utilisateur non connecté ne peut pas accéder au dashboard.
        #
        # Il doit être redirigé vers la page de connexion avec un paramètre "next"
        # contenant l'URL du dashboard demandée.
        response = self.client.get(reverse("dashboard:home"))

        # Vérifie que la redirection pointe vers la page de connexion.
        #
        # Le paramètre next permet à Django de savoir où renvoyer l'utilisateur
        # après une connexion réussie.
        self.assertRedirects(
            response,
            f"{reverse('accounts:connexion')}?next={reverse('dashboard:home')}",
        )

    def test_normal_user_cannot_access_dashboard(self):
        # Vérifie qu'un utilisateur connecté mais non staff ne peut pas
        # accéder au dashboard.

        # Connecte l'utilisateur simple dans le client de test.
        self.client.force_login(self.user)

        # Tente d'accéder à l'accueil du dashboard.
        response = self.client.get(reverse("dashboard:home"))

        # Un utilisateur connecté mais non autorisé doit recevoir une erreur 403.
        self.assertEqual(response.status_code, 403)

    def test_staff_user_can_access_dashboard(self):
        # Vérifie qu'un utilisateur staff peut accéder au dashboard.

        # Connecte l'utilisateur staff.
        self.client.force_login(self.staff)

        # Charge l'accueil du dashboard.
        response = self.client.get(reverse("dashboard:home"))

        # La page doit être accessible.
        self.assertEqual(response.status_code, 200)

        # Vérifie que le contenu attendu du dashboard est présent.
        self.assertContains(response, "Dashboard administrateur")

    def test_superuser_can_access_dashboard_and_see_link(self):
        # Vérifie qu'un superuser peut accéder au dashboard
        # et voit le lien du dashboard sur la page d'accueil publique.

        # Connecte le superuser.
        self.client.force_login(self.superuser)

        # Charge l'accueil du dashboard.
        dashboard_response = self.client.get(reverse("dashboard:home"))

        # Charge la page d'accueil publique des films.
        home_response = self.client.get(reverse("movies:accueil"))

        # Le superuser doit pouvoir accéder au dashboard.
        self.assertEqual(dashboard_response.status_code, 200)

        # Le lien vers le dashboard doit être visible dans l'interface.
        self.assertContains(home_response, reverse("dashboard:home"))

        # Vérifie aussi la présence du texte associé au lien.
        self.assertContains(home_response, "Dashboard")

    def test_normal_user_cannot_access_sensitive_dashboard_url(self):
        # Vérifie qu'un utilisateur simple ne peut pas accéder directement
        # à une URL sensible du dashboard, même s'il connaît son chemin.

        # Connecte l'utilisateur simple.
        self.client.force_login(self.user)

        # Tente d'accéder directement à la page de création d'un film.
        response = self.client.get(reverse("dashboard:film_create"))

        # L'accès doit être interdit.
        self.assertEqual(response.status_code, 403)

    def test_normal_user_cannot_access_movie_list(self):
        # Vérifie que la liste des films reste protégée pour un utilisateur non staff.
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard:film_list"))

        self.assertEqual(response.status_code, 403)

    def test_normal_user_cannot_access_comment_list(self):
        # Vérifie que la liste de modération des commentaires reste protégée.
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard:commentaire_list"))

        self.assertEqual(response.status_code, 403)

    def test_dashboard_link_is_visible_for_staff_user(self):
        # Vérifie que le lien vers le dashboard est affiché
        # pour un utilisateur staff sur la page d'accueil publique.

        # Connecte l'utilisateur staff.
        self.client.force_login(self.staff)

        # Charge la page d'accueil des films.
        response = self.client.get(reverse("movies:accueil"))

        # Vérifie que l'URL du dashboard est présente dans le HTML.
        self.assertContains(response, reverse("dashboard:home"))

        # Vérifie que le texte "Dashboard" est visible.
        self.assertContains(response, "Dashboard")

    def test_dashboard_link_is_absent_for_normal_user(self):
        # Vérifie qu'un utilisateur normal ne voit pas le lien vers le dashboard.
        #
        # Même si la protection serveur existe déjà, masquer le lien améliore
        # l'expérience utilisateur et évite de proposer une action interdite.

        # Connecte l'utilisateur simple.
        self.client.force_login(self.user)

        # Charge la page d'accueil des films.
        response = self.client.get(reverse("movies:accueil"))

        # L'URL du dashboard ne doit pas apparaître dans le HTML.
        self.assertNotContains(response, reverse("dashboard:home"))

        # Le texte "Dashboard" ne doit pas non plus apparaître.
        self.assertNotContains(response, "Dashboard")


class DashboardFunctionalTests(TestCase):
    # Cette classe regroupe les tests fonctionnels du dashboard.
    #
    # Contrairement à DashboardAccessTests, qui vérifie surtout les permissions,
    # cette classe vérifie les actions concrètes réalisables par un utilisateur staff :
    # - affichage et filtrage des critiques ;
    # - création, modification et suppression de films ;
    # - synchronisation du casting ;
    # - protection contre la suppression de genres ou acteurs encore utilisés ;
    # - suppression de critiques et commentaires ;
    # - mise à jour des statistiques ;
    # - affichage des statistiques sur l'accueil du dashboard.

    def setUp(self):
        # setUp prépare un mini-jeu de données complet avant chaque test.
        #
        # On crée :
        # - un utilisateur staff connecté ;
        # - un utilisateur simple auteur d'une critique et d'un commentaire ;
        # - un genre ;
        # - un acteur ;
        # - un film ;
        # - un casting ;
        # - une critique ;
        # - un commentaire.
        #
        # Cela permet à chaque test de partir d'un état cohérent et isolé.

        # Récupère le modèle utilisateur actif du projet.
        User = get_user_model()

        # Crée l'utilisateur staff qui exécutera les actions du dashboard.
        self.staff = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="password",
            is_staff=True,
        )

        # Crée un utilisateur normal qui servira d'auteur
        # pour les critiques et commentaires.
        self.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password",
        )

        # Crée un genre utilisé par le film de test.
        self.genre = Genre.objects.create(nom="Drame")

        # Crée un acteur utilisé dans le casting du film.
        self.actor = Acteur.objects.create(nom="Camille Durand")

        # Crée un film de test.
        self.film = Film.objects.create(
            titre="Nuit rouge",
            synopsis="Une enquête nocturne.",
            genre=self.genre,
            date_sortie="2024-01-10",
            duree_minutes=120,
        )

        # Associe l'acteur au film via le modèle intermédiaire Casting.
        Casting.objects.create(film=self.film, acteur=self.actor)

        # Crée une critique liée au film et à l'utilisateur simple.
        self.critique = Critique.objects.create(
            film=self.film,
            utilisateur=self.user,
            titre="Très réussi",
            texte="Une critique complète.",
            note=4,
        )

        # Crée un commentaire lié à la critique.
        self.commentaire = Commentaire.objects.create(
            critique=self.critique,
            utilisateur=self.user,
            texte="Je partage cet avis.",
        )

        # Connecte automatiquement l'utilisateur staff.
        #
        # Tous les tests de cette classe partent du principe que l'accès
        # au dashboard est déjà autorisé.
        self.client.force_login(self.staff)

    def test_review_list_displays_film_author_and_note_selects(self):
        # Vérifie que la liste des critiques affiche bien trois filtres
        # sous forme de menus déroulants :
        # - film ;
        # - auteur ;
        # - note.

        # Charge la page de liste des critiques du dashboard.
        response = self.client.get(reverse("dashboard:critique_list"))

        # Vérifie la présence du select de filtre par film.
        self.assertContains(
            response,
            '<select id="film" name="film" class="form-control">',
        )

        # Vérifie la présence du select de filtre par auteur.
        self.assertContains(
            response,
            '<select id="auteur" name="auteur" class="form-control">',
        )

        # Vérifie la présence du select de filtre par note.
        self.assertContains(
            response,
            '<select id="note" name="note" class="form-control">',
        )

        # Vérifie la présence de l'option permettant de ne filtrer par aucun film.
        self.assertContains(response, "Tous les films")

        # Vérifie la présence de l'option permettant de ne filtrer par aucun auteur.
        self.assertContains(response, "Tous les auteurs")

    def test_review_list_filters_by_selected_movie(self):
        # Vérifie que la liste des critiques peut être filtrée par film.

        # Crée un second film pour s'assurer que le filtre exclut
        # les critiques des autres films.
        other_film = Film.objects.create(
            titre="Aube froide",
            synopsis="Un autre film.",
            genre=self.genre,
            date_sortie="2025-02-01",
            duree_minutes=98,
        )

        # Crée une critique liée à cet autre film.
        Critique.objects.create(
            film=other_film,
            utilisateur=self.user,
            titre="Avis sur Aube froide",
            texte="Une autre critique.",
            note=3,
        )

        # Charge la liste des critiques avec le filtre film correspondant
        # au film principal du setUp.
        response = self.client.get(
            reverse("dashboard:critique_list"),
            {"film": str(self.film.pk)},
        )

        # Vérifie que seule la critique du film sélectionné est retournée.
        self.assertEqual(list(response.context["critiques"]), [self.critique])

        # Vérifie que l'option du film sélectionné est bien marquée comme selected
        # dans le HTML du formulaire de filtre.
        self.assertContains(
            response,
            f'<option value="{self.film.pk}" selected>',
        )

    def test_review_list_filters_by_selected_author(self):
        # Vérifie que la liste des critiques peut être filtrée par auteur.

        # Récupère le modèle utilisateur actif.
        User = get_user_model()

        # Crée un autre utilisateur.
        other_user = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="password",
        )

        # Crée une critique écrite par cet autre utilisateur.
        Critique.objects.create(
            film=self.film,
            utilisateur=other_user,
            titre="Un autre avis",
            texte="Une autre critique.",
            note=2,
        )

        # Charge la liste des critiques avec un filtre sur l'auteur principal.
        response = self.client.get(
            reverse("dashboard:critique_list"),
            {"auteur": str(self.user.pk)},
        )

        # Vérifie que seule la critique de self.user est retournée.
        self.assertEqual(list(response.context["critiques"]), [self.critique])

        # Vérifie que l'option de l'auteur sélectionné est marquée selected.
        self.assertContains(
            response,
            f'<option value="{self.user.pk}" selected>',
        )

    def test_review_list_filters_by_selected_note(self):
        # Vérifie que la liste des critiques peut être filtrée par note.

        # Récupère le modèle utilisateur actif.
        User = get_user_model()

        # Crée un autre utilisateur pour produire une deuxième critique.
        other_user = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="password",
        )

        # Crée une critique avec une note différente de celle de self.critique.
        Critique.objects.create(
            film=self.film,
            utilisateur=other_user,
            titre="Un autre avis",
            texte="Une autre critique.",
            note=2,
        )

        # Charge la liste des critiques avec un filtre sur la note 4.
        response = self.client.get(
            reverse("dashboard:critique_list"),
            {"note": "4"},
        )

        # Vérifie que seule la critique ayant la note 4 est retournée.
        self.assertEqual(list(response.context["critiques"]), [self.critique])

        # Vérifie que l'option de note 4 est marquée selected.
        self.assertContains(response, '<option value="4" selected>')

    def test_review_list_ignores_invalid_filter_values(self):
        # Vérifie que des valeurs de filtre invalides ne cassent pas la page.
        #
        # Exemple :
        # - film="invalide" n'est pas un identifiant numérique ;
        # - auteur="-1" ne correspond à aucun auteur valable ;
        # - note="9" est hors plage si les notes attendues sont limitées.
        #
        # Le comportement attendu ici est de ne pas appliquer ces filtres invalides
        # et d'afficher les critiques existantes.

        # Récupère le modèle utilisateur actif.
        User = get_user_model()

        # Crée un autre utilisateur.
        other_user = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="password",
        )

        # Crée une deuxième critique afin de vérifier que les deux critiques
        # restent visibles si les filtres sont invalides.
        other_review = Critique.objects.create(
            film=self.film,
            utilisateur=other_user,
            titre="Un autre avis",
            texte="Une autre critique.",
            note=2,
        )

        # Envoie volontairement des valeurs invalides dans les paramètres GET.
        response = self.client.get(
            reverse("dashboard:critique_list"),
            {"film": "invalide", "auteur": "-1", "note": "9"},
        )

        # La page doit rester accessible.
        self.assertEqual(response.status_code, 200)

        # Les deux critiques doivent être présentes dans le contexte.
        self.assertEqual(
            set(response.context["critiques"]),
            {self.critique, other_review},
        )

    def test_staff_can_access_comment_list(self):
        # Vérifie qu'un utilisateur staff peut accéder à la liste des commentaires.
        response = self.client.get(reverse("dashboard:commentaire_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Commentaires")
        self.assertContains(response, "Je partage cet avis.")
        self.assertContains(response, '<input id="q" name="q" type="search"')
        self.assertContains(response, '<select id="film" name="film" class="form-control">')
        self.assertContains(response, '<select id="auteur" name="auteur" class="form-control">')
        self.assertContains(response, '<select id="critique" name="critique" class="form-control">')

    def test_comment_list_filters_by_text(self):
        # Vérifie que la recherche porte sur le texte du commentaire.
        Commentaire.objects.create(
            critique=self.critique,
            utilisateur=self.user,
            texte="Un commentaire sans le mot recherché.",
        )

        response = self.client.get(
            reverse("dashboard:commentaire_list"),
            {"q": "partage"},
        )

        self.assertEqual(list(response.context["commentaires"]), [self.commentaire])
        self.assertContains(response, "Je partage cet avis.")
        self.assertNotContains(response, "Un commentaire sans le mot recherché.")
        self.assertContains(response, 'value="partage"')

    def test_comment_list_filters_by_movie(self):
        # Vérifie le filtre par film concerné par la critique commentée.
        other_film = Film.objects.create(
            titre="Aube froide",
            synopsis="Un autre film.",
            genre=self.genre,
            date_sortie="2025-02-01",
            duree_minutes=98,
        )
        other_review = Critique.objects.create(
            film=other_film,
            utilisateur=self.user,
            titre="Avis sur Aube froide",
            texte="Une autre critique.",
            note=3,
        )
        Commentaire.objects.create(
            critique=other_review,
            utilisateur=self.user,
            texte="Commentaire sur un autre film.",
        )

        response = self.client.get(
            reverse("dashboard:commentaire_list"),
            {"film": str(self.film.pk)},
        )

        self.assertEqual(list(response.context["commentaires"]), [self.commentaire])
        self.assertContains(response, "Nuit rouge")
        self.assertNotContains(response, "Commentaire sur un autre film.")
        self.assertContains(response, f'<option value="{self.film.pk}" selected>')

    def test_comment_list_filters_by_author(self):
        # Vérifie le filtre par auteur du commentaire.
        User = get_user_model()
        other_user = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="password",
        )
        Commentaire.objects.create(
            critique=self.critique,
            utilisateur=other_user,
            texte="Commentaire écrit par Bob.",
        )

        response = self.client.get(
            reverse("dashboard:commentaire_list"),
            {"auteur": str(self.user.pk)},
        )

        self.assertEqual(list(response.context["commentaires"]), [self.commentaire])
        self.assertContains(response, "alice")
        self.assertNotContains(response, "Commentaire écrit par Bob.")
        self.assertContains(response, f'<option value="{self.user.pk}" selected>')

    def test_comment_list_combines_filters(self):
        # Vérifie qu'une combinaison de filtres limite correctement les résultats.
        User = get_user_model()
        other_user = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="password",
        )
        other_film = Film.objects.create(
            titre="Aube froide",
            synopsis="Un autre film.",
            genre=self.genre,
            date_sortie="2025-02-01",
            duree_minutes=98,
        )
        other_review = Critique.objects.create(
            film=other_film,
            utilisateur=other_user,
            titre="Avis sur Aube froide",
            texte="Une autre critique.",
            note=2,
        )
        matching_comment = Commentaire.objects.create(
            critique=self.critique,
            utilisateur=self.user,
            texte="Ce passage contient un spoiler précis.",
        )
        Commentaire.objects.create(
            critique=other_review,
            utilisateur=self.user,
            texte="Spoiler sur un autre film.",
        )
        Commentaire.objects.create(
            critique=self.critique,
            utilisateur=other_user,
            texte="Spoiler écrit par un autre auteur.",
        )

        response = self.client.get(
            reverse("dashboard:commentaire_list"),
            {
                "q": "spoiler",
                "film": str(self.film.pk),
                "auteur": str(self.user.pk),
            },
        )

        self.assertEqual(list(response.context["commentaires"]), [matching_comment])
        self.assertContains(response, "Ce passage contient un spoiler précis.")
        self.assertNotContains(response, "Spoiler sur un autre film.")
        self.assertNotContains(response, "Spoiler écrit par un autre auteur.")

    def test_comment_list_ignores_invalid_filter_values(self):
        # Vérifie que les valeurs invalides sont ignorées sans casser la page.
        other_comment = Commentaire.objects.create(
            critique=self.critique,
            utilisateur=self.user,
            texte="Un second commentaire visible.",
        )

        response = self.client.get(
            reverse("dashboard:commentaire_list"),
            {"film": "invalide", "auteur": "-1", "critique": "999999"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.context["commentaires"]),
            {self.commentaire, other_comment},
        )

    def test_comment_list_empty_state_with_filters(self):
        # Vérifie le message affiché lorsqu'aucun commentaire ne correspond.
        response = self.client.get(
            reverse("dashboard:commentaire_list"),
            {"q": "aucun-resultat"},
        )

        self.assertEqual(list(response.context["commentaires"]), [])
        self.assertContains(
            response,
            "Aucun commentaire ne correspond aux critères sélectionnés.",
        )

    def test_staff_can_access_movie_list(self):
        response = self.client.get(reverse("dashboard:film_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Films")
        self.assertContains(response, "Nuit rouge")
        self.assertContains(response, '<input id="q" name="q" type="search"')
        self.assertContains(response, '<select id="genre" name="genre" class="form-control">')
        self.assertContains(response, '<select id="annee" name="annee" class="form-control">')

    def test_movie_list_filters_by_title(self):
        other_film = Film.objects.create(
            titre="Aube froide",
            synopsis="Un autre film.",
            genre=self.genre,
            date_sortie="2025-02-01",
            duree_minutes=98,
        )

        response = self.client.get(reverse("dashboard:film_list"), {"q": "Nuit"})

        self.assertEqual(list(response.context["films"]), [self.film])
        self.assertContains(response, "Nuit rouge")
        self.assertNotContains(response, "Aube froide")

    def test_movie_list_filters_by_genre(self):
        other_genre = Genre.objects.create(nom="Action")
        other_film = Film.objects.create(
            titre="Course finale",
            synopsis="Un autre film.",
            genre=other_genre,
            date_sortie="2025-02-01",
            duree_minutes=98,
        )

        response = self.client.get(
            reverse("dashboard:film_list"),
            {"genre": str(self.genre.pk)},
        )

        self.assertEqual(list(response.context["films"]), [self.film])
        self.assertContains(response, "Nuit rouge")
        self.assertNotContains(response, "Course finale")

    def test_movie_list_filters_by_year(self):
        other_film = Film.objects.create(
            titre="Aube froide",
            synopsis="Un autre film.",
            genre=self.genre,
            date_sortie="2025-02-01",
            duree_minutes=98,
        )

        response = self.client.get(reverse("dashboard:film_list"), {"annee": "2024"})

        self.assertEqual(list(response.context["films"]), [self.film])
        self.assertContains(response, "Nuit rouge")
        self.assertNotContains(response, "Aube froide")

    def test_movie_list_combines_search_and_genre_filters(self):
        other_genre = Genre.objects.create(nom="Action")
        excluded_film = Film.objects.create(
            titre="Nuit rapide",
            synopsis="Un film d'action.",
            genre=other_genre,
            date_sortie="2024-03-01",
            duree_minutes=100,
        )

        response = self.client.get(
            reverse("dashboard:film_list"),
            {"q": "Nuit", "genre": str(self.genre.pk)},
        )

        self.assertEqual(list(response.context["films"]), [self.film])
        self.assertContains(response, "Nuit rouge")
        self.assertNotContains(response, "Nuit rapide")

    def test_staff_can_add_movie_and_sync_casting(self):
        # Vérifie qu'un utilisateur staff peut créer un film
        # et associer correctement des acteurs via le formulaire.

        # Soumet le formulaire de création de film.
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

        # Après création, l'utilisateur doit être redirigé vers la liste des films.
        self.assertRedirects(response, reverse("dashboard:film_list"))

        # Récupère le film nouvellement créé.
        film = Film.objects.get(titre="Aube froide")

        # Un nouveau film sans critique doit avoir une note moyenne vide.
        self.assertEqual(film.note_moyenne, None)

        # Un nouveau film sans critique doit avoir zéro critique.
        self.assertEqual(film.nombre_critiques, 0)

        # Vérifie que le casting avec l'acteur sélectionné a bien été créé.
        self.assertTrue(Casting.objects.filter(film=film, acteur=self.actor).exists())

    def test_staff_can_update_movie_and_sync_casting(self):
        # Vérifie qu'un utilisateur staff peut modifier un film
        # et que le casting est correctement synchronisé.

        # Crée un second acteur qui remplacera l'acteur initial.
        other_actor = Acteur.objects.create(nom="Louis Martin")

        # Soumet le formulaire de modification du film existant.
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

        # Après modification, l'utilisateur doit être redirigé vers la liste des films.
        self.assertRedirects(response, reverse("dashboard:film_list"))

        # Recharge le film depuis la base pour récupérer les modifications.
        self.film.refresh_from_db()

        # Vérifie que le titre a bien été modifié.
        self.assertEqual(self.film.titre, "Nuit rouge restaurée")

        # Vérifie que l'ancien acteur n'est plus associé au film.
        self.assertFalse(
            Casting.objects.filter(film=self.film, acteur=self.actor).exists()
        )

        # Vérifie que le nouvel acteur est bien associé au film.
        self.assertTrue(
            Casting.objects.filter(film=self.film, acteur=other_actor).exists()
        )

    def test_staff_can_delete_movie(self):
        # Vérifie qu'un utilisateur staff peut supprimer un film.
        #
        # Ce test vérifie aussi les suppressions en cascade :
        # - la critique liée au film doit disparaître ;
        # - le commentaire lié à la critique doit disparaître.

        # Envoie une requête POST de suppression du film.
        response = self.client.post(reverse("dashboard:film_delete", args=[self.film.pk]))

        # Après suppression, l'utilisateur doit être redirigé vers la liste des films.
        self.assertRedirects(response, reverse("dashboard:film_list"))

        # Vérifie que le film n'existe plus.
        self.assertFalse(Film.objects.filter(pk=self.film.pk).exists())

        # Vérifie que la critique associée au film a aussi été supprimée.
        self.assertFalse(Critique.objects.filter(pk=self.critique.pk).exists())

        # Vérifie que le commentaire associé à la critique a aussi été supprimé.
        self.assertFalse(Commentaire.objects.filter(pk=self.commentaire.pk).exists())

    def test_used_genre_cannot_be_deleted(self):
        # Vérifie qu'un genre encore utilisé par au moins un film
        # ne peut pas être supprimé depuis le dashboard.

        # Tente de supprimer le genre utilisé par self.film.
        #
        # follow=True permet de suivre la redirection afin de vérifier
        # le message affiché après l'échec de suppression.
        response = self.client.post(
            reverse("dashboard:genre_delete", args=[self.genre.pk]),
            follow=True,
        )

        # Vérifie que l'utilisateur est redirigé vers la liste des genres.
        self.assertRedirects(response, reverse("dashboard:genre_list"))

        # Vérifie que le genre existe toujours en base.
        self.assertTrue(Genre.objects.filter(pk=self.genre.pk).exists())

        # Vérifie que le message d'erreur attendu est affiché.
        self.assertContains(
            response,
            "Ce genre est encore utilisé par un ou plusieurs films.",
        )

    def test_actor_used_in_casting_cannot_be_deleted(self):
        # Vérifie qu'un acteur encore associé à un film via un casting
        # ne peut pas être supprimé.

        # Tente de supprimer l'acteur utilisé dans le casting du film.
        #
        # follow=True permet de vérifier le message affiché après redirection.
        response = self.client.post(
            reverse("dashboard:acteur_delete", args=[self.actor.pk]),
            follow=True,
        )

        # Vérifie que l'utilisateur est redirigé vers la liste des acteurs.
        self.assertRedirects(response, reverse("dashboard:acteur_list"))

        # Vérifie que l'acteur existe toujours en base.
        self.assertTrue(Acteur.objects.filter(pk=self.actor.pk).exists())

        # Vérifie que le message d'erreur attendu est affiché.
        self.assertContains(
            response,
            "Cet acteur est encore associé à un ou plusieurs films.",
        )

    def test_staff_can_delete_review(self):
        # Vérifie qu'un utilisateur staff peut supprimer une critique
        # depuis le dashboard.

        # Envoie une requête POST de suppression de critique.
        response = self.client.post(
            reverse("dashboard:critique_delete", args=[self.critique.pk])
        )

        # Après suppression, l'utilisateur doit être redirigé vers la liste des critiques.
        self.assertRedirects(response, reverse("dashboard:critique_list"))

        # Vérifie que la critique n'existe plus en base.
        self.assertFalse(Critique.objects.filter(pk=self.critique.pk).exists())

    def test_review_delete_confirmation_get_does_not_delete(self):
        # Vérifie que l'accès en GET à la page de suppression d'une critique
        # affiche seulement une confirmation et ne supprime rien.
        #
        # Cela protège contre les suppressions accidentelles par simple ouverture d'URL.

        # Charge la page de confirmation de suppression.
        response = self.client.get(
            reverse("dashboard:critique_delete", args=[self.critique.pk])
        )

        # La page de confirmation doit être accessible.
        self.assertEqual(response.status_code, 200)

        # La critique doit toujours exister après une requête GET.
        self.assertTrue(Critique.objects.filter(pk=self.critique.pk).exists())

        # Vérifie que la page affiche bien un texte de confirmation.
        self.assertContains(response, "Supprimer la critique")

    def test_review_delete_updates_movie_statistics(self):
        # Vérifie que la suppression d'une critique met à jour
        # les statistiques du film concerné.
        #
        # Avant suppression :
        # - le film possède 1 critique ;
        # - la note moyenne vaut 4.
        #
        # Après suppression :
        # - le film possède 0 critique ;
        # - la note moyenne redevient None.

        # Vérifie l'état initial du film.
        self.assertEqual(self.film.nombre_critiques, 1)
        self.assertEqual(self.film.note_moyenne, 4)

        # Supprime la critique.
        self.client.post(reverse("dashboard:critique_delete", args=[self.critique.pk]))

        # Recharge le film depuis la base pour récupérer les statistiques recalculées.
        self.film.refresh_from_db()

        # Vérifie que le compteur de critiques est revenu à zéro.
        self.assertEqual(self.film.nombre_critiques, 0)

        # Vérifie que la note moyenne est revenue à None.
        self.assertIsNone(self.film.note_moyenne)

    def test_comment_delete_confirmation_get_does_not_delete(self):
        # Vérifie que l'accès en GET à la suppression d'un commentaire
        # affiche une page de confirmation sans supprimer le commentaire.

        # Charge la page de confirmation de suppression du commentaire.
        response = self.client.get(
            reverse("dashboard:commentaire_delete", args=[self.commentaire.pk])
        )

        # La page doit être accessible.
        self.assertEqual(response.status_code, 200)

        # Le commentaire doit toujours exister après une requête GET.
        self.assertTrue(Commentaire.objects.filter(pk=self.commentaire.pk).exists())

        # Vérifie que la page contient le texte de confirmation attendu.
        self.assertContains(response, "Supprimer le commentaire")

    def test_staff_can_delete_comment_with_post(self):
        # Vérifie qu'un utilisateur staff peut supprimer un commentaire
        # avec une requête POST.

        # Envoie une requête POST de suppression du commentaire.
        response = self.client.post(
            reverse("dashboard:commentaire_delete", args=[self.commentaire.pk])
        )

        # Après suppression, redirection vers la liste des commentaires.
        self.assertRedirects(response, reverse("dashboard:commentaire_list"))

        # Vérifie que le commentaire a bien été supprimé.
        self.assertFalse(Commentaire.objects.filter(pk=self.commentaire.pk).exists())

    def test_dashboard_home_displays_statistics(self):
        # Vérifie que la page d'accueil du dashboard affiche correctement
        # les statistiques globales et les derniers contenus.

        # Charge l'accueil du dashboard.
        response = self.client.get(reverse("dashboard:home"))

        # La page doit répondre correctement.
        self.assertEqual(response.status_code, 200)

        # Vérifie le nombre de films affiché dans le contexte.
        self.assertEqual(response.context["nombre_films"], 1)

        # Vérifie le nombre de critiques affiché dans le contexte.
        self.assertEqual(response.context["nombre_critiques"], 1)

        # Vérifie le nombre de commentaires affiché dans le contexte.
        self.assertEqual(response.context["nombre_commentaires"], 1)

        # Vérifie le nombre d'utilisateurs affiché dans le contexte.
        #
        # Il y a ici deux utilisateurs :
        # - staff ;
        # - alice.
        self.assertEqual(response.context["nombre_utilisateurs"], 2)

        # Vérifie que le film récent apparaît dans la page.
        self.assertContains(response, "Nuit rouge")

        # Vérifie que le commentaire récent apparaît aussi dans la page.
        self.assertContains(response, "Je partage cet avis.")
