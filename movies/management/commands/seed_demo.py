from datetime import date
from html import escape

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from movies.models import Acteur, Casting, Commentaire, Critique, Film, Genre


PASSWORD = "DemoPass123!"

GENRES = [
    "Action",
    "Aventure",
    "Comédie",
    "Drame",
    "Fantastique",
    "Horreur",
    "Romance",
    "Science-fiction",
    "Thriller",
    "Animation",
]

ACTEURS = [
    "Nora Diallo",
    "Karim Benali",
    "Aminata Camara",
    "Lucas Morel",
    "Sofia Laurent",
    "Ibrahim Barry",
    "Maya Dupont",
    "Yacine Traoré",
    "Clara Martin",
    "Hugo Bernard",
    "Fatoumata Sow",
    "Samuel Leroy",
    "Inès Kaba",
    "Adam Fournier",
    "Lina Conte",
    "Mamadou Keita",
    "Élise Garnier",
    "Ousmane Bah",
    "Sarah Petit",
    "Thomas Vidal",
]

FILMS = [
    ("Démo — L'Écho des Étoiles", "Science-fiction", 2024, 142),
    ("Démo — Minuit sur Conakry", "Drame", 2023, 118),
    ("Démo — Le Dernier Signal", "Thriller", 2022, 126),
    ("Démo — Rires en Coulisses", "Comédie", 2021, 101),
    ("Démo — La Cité des Ombres", "Action", 2020, 132),
    ("Démo — Horizon Perdu", "Aventure", 2019, 124),
    ("Démo — Souvenirs d'Automne", "Romance", 2018, 109),
    ("Démo — Le Masque d'Argile", "Fantastique", 2024, 115),
    ("Démo — Chambre 404", "Horreur", 2023, 96),
    ("Démo — Planète Verre", "Science-fiction", 2022, 138),
    ("Démo — Le Pont des Silences", "Drame", 2021, 112),
    ("Démo — Turbo Panique", "Action", 2020, 121),
    ("Démo — Les Petits Géants", "Animation", 2019, 88),
    ("Démo — Lettre à Demain", "Romance", 2018, 104),
    ("Démo — Le Cercle Rouge", "Thriller", 2017, 117),
    ("Démo — Voyage Sans Carte", "Aventure", 2016, 130),
    ("Démo — La Nuit des Lanternes", "Fantastique", 2015, 119),
    ("Démo — Café des Miracles", "Comédie", 2014, 98),
    ("Démo — Sous le Même Ciel", "Drame", 2013, 123),
    ("Démo — Fréquence Zéro", "Science-fiction", 2012, 127),
    ("Démo — Le Rire du Monstre", "Horreur", 2011, 94),
    ("Démo — Dernière Course", "Action", 2010, 110),
    ("Démo — Les Ailes du Fleuve", "Animation", 2009, 92),
    ("Démo — Mémoire de Sable", "Drame", 2008, 116),
    ("Démo — Code Boréal", "Thriller", 2007, 121),
    ("Démo — L'Île des Brumes", "Aventure", 2006, 129),
    ("Démo — Romance à Minuit", "Romance", 2005, 103),
    ("Démo — Royaume Suspendu", "Fantastique", 2004, 133),
    ("Démo — Éclats de Rire", "Comédie", 2003, 97),
    ("Démo — Station Obscure", "Horreur", 2002, 99),
]

CRITIQUE_TITRES = [
    "Une très belle surprise",
    "Un film solide et maîtrisé",
    "Une ambiance remarquable",
    "Des idées intéressantes",
    "Un rythme parfois inégal",
    "Une mise en scène efficace",
    "Une œuvre touchante",
    "Un divertissement réussi",
    "Un scénario captivant",
    "Une expérience mémorable",
]

COMMENTAIRES = [
    "Je partage totalement cet avis.",
    "Ton analyse est intéressante, surtout sur la mise en scène.",
    "Je n'avais pas vu cet aspect du film comme ça.",
    "Bonne critique, ça donne envie de revoir le film.",
    "Je suis un peu moins convaincu, mais ton argument est clair.",
    "Le passage sur les personnages est très pertinent.",
    "Je suis d'accord avec la note donnée.",
    "Cette critique résume bien mon ressenti.",
]

SYNOPSIS_BASE = (
    "Dans un univers marqué par des choix difficiles, les personnages doivent "
    "affronter leurs doutes, leurs ambitions et les conséquences de leurs actes. "
    "Entre tension dramatique, émotions sincères et mise en scène immersive, "
    "ce film propose une expérience pensée pour nourrir les discussions entre cinéphiles."
)


def wrap_title(title, size=18):
    words = title.replace("Démo — ", "").split()
    lines = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > size and current:
            lines.append(current)
            current = word
        else:
            current = candidate

    if current:
        lines.append(current)

    return lines[:4]


def make_svg_poster(title, genre, index):
    palettes = [
        ("#8B2942", "#A6674E", "#1A1816"),
        ("#3D6666", "#8B2942", "#1A1816"),
        ("#6B1F33", "#A84E63", "#211E1C"),
        ("#2A2622", "#A6674E", "#8B2942"),
        ("#1C1816", "#3D6666", "#A84E63"),
    ]
    c1, c2, c3 = palettes[index % len(palettes)]
    title_lines = wrap_title(title)

    text_svg = ""
    y = 390
    for line in title_lines:
        text_svg += (
            f'<text x="300" y="{y}" text-anchor="middle" '
            f'font-family="Arial, sans-serif" font-size="42" '
            f'font-weight="700" fill="white">{escape(line)}</text>'
        )
        y += 52

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="900" viewBox="0 0 600 900">
    <defs>
        <linearGradient id="g{index}" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="{c1}"/>
            <stop offset="55%" stop-color="{c2}"/>
            <stop offset="100%" stop-color="{c3}"/>
        </linearGradient>
    </defs>
    <rect width="600" height="900" fill="url(#g{index})"/>
    <circle cx="470" cy="120" r="120" fill="rgba(255,255,255,0.10)"/>
    <circle cx="120" cy="740" r="180" fill="rgba(0,0,0,0.18)"/>
    <rect x="45" y="45" width="510" height="810" rx="34" fill="none" stroke="rgba(255,255,255,0.28)" stroke-width="4"/>
    <text x="300" y="260" text-anchor="middle" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="rgba(255,255,255,0.78)">MOVIE REVIEW</text>
    {text_svg}
    <text x="300" y="735" text-anchor="middle" font-family="Arial, sans-serif" font-size="28" font-weight="600" fill="rgba(255,255,255,0.80)">{escape(genre)}</text>
    <text x="300" y="790" text-anchor="middle" font-family="Arial, sans-serif" font-size="20" fill="rgba(255,255,255,0.62)">Affiche fictive générée</text>
</svg>"""


class Command(BaseCommand):
    help = "Insère des données fictives complètes pour tester Movie Review dans le navigateur."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep-existing-demo",
            action="store_true",
            help="Ne supprime pas les anciennes données de démo avant insertion.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not options["keep_existing_demo"]:
            self.stdout.write("Nettoyage des anciennes données de démo...")
            Commentaire.objects.filter(utilisateur__username__startswith="demo_").delete()
            Critique.objects.filter(utilisateur__username__startswith="demo_").delete()
            Film.objects.filter(titre__startswith="Démo —").delete()
            get_user_model().objects.filter(username__startswith="demo_").delete()

        self.stdout.write("Création des genres...")
        genres = {
            nom: Genre.objects.get_or_create(nom=nom)[0]
            for nom in GENRES
        }

        self.stdout.write("Création des acteurs...")
        acteurs = {
            nom: Acteur.objects.get_or_create(nom=nom)[0]
            for nom in ACTEURS
        }
        acteurs_list = list(acteurs.values())

        self.stdout.write("Création des utilisateurs de démo...")
        User = get_user_model()

        admin, _ = User.objects.get_or_create(
            username="demo_admin",
            defaults={"email": "demo_admin@example.com", "is_staff": True, "is_superuser": True},
        )
        admin.email = "demo_admin@example.com"
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password(PASSWORD)
        admin.save()

        users = []
        for i in range(1, 13):
            user, _ = User.objects.get_or_create(
                username=f"demo_user_{i:02d}",
                defaults={"email": f"demo_user_{i:02d}@example.com"},
            )
            user.email = f"demo_user_{i:02d}@example.com"
            user.set_password(PASSWORD)
            user.save()
            users.append(user)

        self.stdout.write("Création des films, castings et affiches...")
        films = []
        for index, (titre, genre_nom, annee, duree) in enumerate(FILMS, start=1):
            film = Film.objects.create(
                titre=titre,
                synopsis=SYNOPSIS_BASE,
                genre=genres[genre_nom],
                date_sortie=date(annee, ((index - 1) % 12) + 1, min(((index * 2) % 28) + 1, 28)),
                duree_minutes=duree,
            )

            selected_actors = [
                acteurs_list[(index + offset) % len(acteurs_list)]
                for offset in range(4)
            ]
            for acteur in selected_actors:
                Casting.objects.get_or_create(film=film, acteur=acteur)

            slug = slugify(titre) or f"film-demo-{index}"
            storage_path = f"affiches/demo/{slug}.svg"
            if default_storage.exists(storage_path):
                default_storage.delete(storage_path)

            poster_svg = make_svg_poster(titre, genre_nom, index)
            film.affiche.save(
                f"demo/{slug}.svg",
                ContentFile(poster_svg.encode("utf-8")),
                save=True,
            )
            films.append(film)

        self.stdout.write("Création des critiques et commentaires...")
        for index, film in enumerate(films, start=1):
            # On laisse volontairement certains films sans critique pour tester "Pas encore noté".
            if index % 7 == 0:
                continue

            nombre_critiques = (index % 10) + 2
            reviewers = users[:nombre_critiques]

            for user_index, user in enumerate(reviewers, start=1):
                note = ((index + user_index) % 5) + 1
                critique = Critique.objects.create(
                    film=film,
                    utilisateur=user,
                    titre=CRITIQUE_TITRES[(index + user_index) % len(CRITIQUE_TITRES)],
                    texte=(
                        "Cette critique fictive sert à tester l'affichage des avis, "
                        "le calcul de la note moyenne, le classement des films et "
                        "les discussions entre utilisateurs. Le film propose plusieurs "
                        "éléments intéressants à analyser, notamment son rythme, ses "
                        "personnages et son ambiance."
                    ),
                    note=note,
                )

                for comment_offset in range((user_index + index) % 3):
                    comment_user = users[(user_index + comment_offset) % len(users)]
                    Commentaire.objects.create(
                        critique=critique,
                        utilisateur=comment_user,
                        texte=COMMENTAIRES[(index + user_index + comment_offset) % len(COMMENTAIRES)],
                    )

        total_films = Film.objects.filter(titre__startswith="Démo —").count()
        total_critiques = Critique.objects.filter(film__titre__startswith="Démo —").count()
        total_commentaires = Commentaire.objects.filter(critique__film__titre__startswith="Démo —").count()

        self.stdout.write(self.style.SUCCESS("Données de démo insérées avec succès."))
        self.stdout.write(f"Films de démo : {total_films}")
        self.stdout.write(f"Critiques de démo : {total_critiques}")
        self.stdout.write(f"Commentaires de démo : {total_commentaires}")
        self.stdout.write("")
        self.stdout.write("Comptes disponibles :")
        self.stdout.write(f"Admin : demo_admin / {PASSWORD}")
        self.stdout.write(f"Utilisateur : demo_user_01 / {PASSWORD}")