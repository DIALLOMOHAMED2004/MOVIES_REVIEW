import argparse
import json
import math
import re
import time
from datetime import date
from urllib import error, parse, request

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction

from movies.models import Acteur, Casting, Commentaire, Critique, Film, Genre
from movies.management.commands.seed_demo import (
    ACTEURS as DEMO_ACTEURS,
    COMMENTAIRES as DEMO_COMMENTAIRES,
    PASSWORD,
)


JIKAN_API_URL = "https://api.jikan.moe/v4"
DEFAULT_SYNOPSIS = (
    "Synopsis indisponible. Cette œuvre d'animation est importée depuis "
    "MyAnimeList via Jikan afin d'alimenter la démonstration Movie Review."
)

PRESENTATION_USERS = [
    ("mal_user_01", "Aminata", "Camara", "la construction des personnages", 0.20),
    ("mal_user_02", "Karim", "Benali", "le rythme narratif", -0.10),
    ("mal_user_03", "Nora", "Diallo", "la mise en scène", 0.10),
    ("mal_user_04", "Lucas", "Morel", "l'animation et le découpage", 0.00),
    ("mal_user_05", "Sofia", "Laurent", "l'émotion finale", 0.30),
    ("mal_user_06", "Ibrahim", "Barry", "la cohérence du scénario", -0.20),
    ("mal_user_07", "Maya", "Dupont", "la musique et l'ambiance", 0.10),
    ("mal_user_08", "Yacine", "Traoré", "les scènes d'action", 0.00),
    ("mal_user_09", "Clara", "Martin", "les dialogues", -0.10),
    ("mal_user_10", "Hugo", "Bernard", "l'univers visuel", 0.20),
    ("mal_user_11", "Fatoumata", "Sow", "le développement thématique", 0.00),
    ("mal_user_12", "Samuel", "Leroy", "la tension dramatique", -0.20),
    ("mal_user_13", "Inès", "Kaba", "la progression des enjeux", 0.10),
    ("mal_user_14", "Adam", "Fournier", "la direction artistique", 0.20),
    ("mal_user_15", "Lina", "Conte", "les relations entre personnages", 0.00),
    ("mal_user_16", "Mamadou", "Keita", "l'originalité du concept", -0.10),
    ("mal_user_17", "Élise", "Garnier", "la profondeur émotionnelle", 0.30),
    ("mal_user_18", "Ousmane", "Bah", "le sens du spectacle", 0.10),
    ("mal_user_19", "Sarah", "Petit", "la fin et ses conséquences", -0.10),
    ("mal_user_20", "Thomas", "Vidal", "la qualité de l'écriture", 0.00),
    ("mal_user_21", "Moussa", "Kaba", "la portée des thèmes", 0.10),
    ("mal_user_22", "Aïcha", "Barry", "l'attachement aux héros", 0.20),
    ("mal_user_23", "Paul", "Renaud", "le montage", -0.20),
    ("mal_user_24", "Mariama", "Diallo", "les moments contemplatifs", 0.00),
    ("mal_user_25", "Noémie", "Petit", "la capacité à surprendre", 0.10),
]

GENRE_ASPECTS = {
    "Action": ["l'énergie des affrontements", "le sens du spectacle", "la lisibilité des scènes fortes"],
    "Adventure": ["le sentiment de voyage", "la découverte progressive du monde", "le goût de l'exploration"],
    "Avant Garde": ["les choix expérimentaux", "la liberté de ton", "la prise de risque visuelle"],
    "Award Winning": ["l'ambition artistique", "la maîtrise générale", "le soin apporté aux détails"],
    "Boys Love": ["la délicatesse des relations", "les non-dits entre personnages", "l'évolution affective"],
    "Comedy": ["le timing comique", "la légèreté des situations", "la dynamique de groupe"],
    "Drama": ["l'intensité émotionnelle", "les conflits intérieurs", "la maturité du récit"],
    "Fantasy": ["la richesse de l'univers", "la magie du cadre", "la cohérence du monde"],
    "Girls Love": ["la subtilité des sentiments", "la sincérité des échanges", "la progression relationnelle"],
    "Gourmet": ["l'ambiance chaleureuse", "les détails du quotidien", "le plaisir sensoriel"],
    "Horror": ["la tension permanente", "l'atmosphère inquiétante", "la gestion du suspense"],
    "Mystery": ["le mystère central", "les indices semés progressivement", "l'envie de comprendre"],
    "Romance": ["la progression sentimentale", "la sincérité des émotions", "les silences entre les personnages"],
    "Sci-Fi": ["les idées de science-fiction", "les implications du concept", "l'équilibre entre spectacle et réflexion"],
    "Slice of Life": ["la douceur du quotidien", "les petits détails humains", "le naturel des interactions"],
    "Sports": ["la montée de l'effort", "l'esprit d'équipe", "la tension des compétitions"],
    "Supernatural": ["la présence du surnaturel", "l'étrangeté de l'ambiance", "le contraste avec le réel"],
    "Suspense": ["la tension psychologique", "la montée du doute", "les retournements de situation"],
}

REVIEW_TITLES = {
    1: [
        "Une promesse qui ne décolle jamais vraiment",
        "Un univers intéressant, mais une exécution trop fragile",
        "Une expérience difficile à recommander",
    ],
    2: [
        "Des idées visibles, mais un résultat inégal",
        "Quelques qualités noyées dans un rythme hésitant",
        "Une œuvre qui fonctionne par moments seulement",
    ],
    3: [
        "Une proposition solide malgré plusieurs limites",
        "Un bon moment, sans être totalement marquant",
        "Une œuvre plaisante qui manque parfois d'ampleur",
    ],
    4: [
        "Une réussite portée par une vraie identité",
        "Un récit maîtrisé et très agréable à suivre",
        "Une œuvre convaincante, généreuse et bien construite",
    ],
    5: [
        "Une œuvre majeure qui justifie sa réputation",
        "Une expérience mémorable du début à la fin",
        "Un incontournable, aussi fort sur le fond que sur la forme",
    ],
}

REVIEW_BODIES = {
    1: [
        (
            "Je comprends ce que {title} essaie de construire, surtout autour de {aspects}. "
            "Malheureusement, l'ensemble m'a paru trop dispersé pour fonctionner pleinement. "
            "Le format {format_label} manque de respiration, et plusieurs scènes semblent avancer sans véritable progression dramatique. "
            "Même avec quelques idées visuelles intéressantes, je suis resté à distance des personnages. "
            "Pour une œuvre sortie en {release_year}, le résultat paraît moins abouti que sa réputation ne le laisse penser."
        ),
        (
            "Le point de départ de {title} pouvait donner quelque chose de fort, mais j'ai trouvé le traitement trop superficiel. "
            "Le récit évoque {aspects}, sans vraiment prendre le temps d'en tirer des moments mémorables. "
            "La réalisation garde quelques passages efficaces, notamment dans l'ambiance, mais l'écriture manque de naturel. "
            "Au final, j'ai eu l'impression de regarder une œuvre qui annonce beaucoup et concrétise assez peu."
        ),
    ],
    2: [
        (
            "{title} possède de vraies qualités, notamment dans {aspects}, mais le résultat reste irrégulier. "
            "Certaines séquences sont très réussies, tandis que d'autres donnent l'impression d'étirer inutilement les enjeux. "
            "J'ai apprécié l'intention et quelques idées de mise en scène, mais les personnages secondaires manquent parfois d'épaisseur. "
            "C'est une œuvre regardable, mais qui aurait gagné à être plus resserrée et plus constante."
        ),
        (
            "Je ne dirais pas que {title} est raté, car son univers et son ambiance ont du charme. "
            "Cependant, l'œuvre hésite trop souvent entre émotion, exposition et spectaculaire. "
            "Le studio {studio} livre plusieurs passages soignés, mais le scénario ne suit pas toujours avec la même précision. "
            "Je retiens quelques moments marquants, sans être totalement convaincu par l'ensemble."
        ),
    ],
    3: [
        (
            "{title} est une œuvre agréable, avec suffisamment de qualités pour maintenir l'intérêt. "
            "J'ai surtout apprécié {aspects}, qui donnent au récit une personnalité identifiable. "
            "Le rythme n'est pas toujours parfait, mais les personnages restent attachants et l'ambiance fonctionne bien. "
            "Ce n'est pas forcément un coup de cœur, mais c'est une proposition solide que je recommanderais aux curieux."
        ),
        (
            "Avec {title}, on sent une vraie envie de raconter quelque chose de sincère. "
            "Le format {format_label} permet de développer quelques idées intéressantes, même si certains arcs restent prévisibles. "
            "Ce qui sauve l'ensemble, c'est la manière dont l'œuvre installe son ton et ses relations. "
            "Je n'ai pas tout trouvé mémorable, mais l'expérience reste globalement positive."
        ),
    ],
    4: [
        (
            "{title} m'a vraiment convaincu par sa maîtrise et par la manière dont il exploite {aspects}. "
            "L'œuvre sait équilibrer progression narrative, émotion et identité visuelle sans perdre son public. "
            "Le travail de {studio} donne une vraie cohérence à l'ensemble, et plusieurs scènes restent en tête après le visionnage. "
            "À mes yeux, c'est une très belle réussite qui mérite largement sa place dans le catalogue."
        ),
        (
            "J'ai trouvé {title} très solide, aussi bien dans son écriture que dans son ambiance. "
            "Le récit prend le temps d'installer ses enjeux, puis récompense l'attention du spectateur avec des moments forts. "
            "Ce que j'ai préféré reste {aspects}, car cela donne une vraie profondeur à l'œuvre. "
            "Sans être parfait, c'est clairement une recommandation facile pour quelqu'un qui aime le genre {genre}."
        ),
    ],
    5: [
        (
            "{title} est le genre d'œuvre qui rappelle pourquoi l'animation peut être aussi puissante. "
            "Tout fonctionne avec une précision impressionnante : {aspects}, la construction émotionnelle et le rythme général. "
            "Le studio {studio} livre une proposition qui ne se contente pas d'être belle, elle sait aussi créer un vrai attachement. "
            "Même après la fin, plusieurs images et décisions narratives restent en mémoire. Pour moi, c'est un incontournable."
        ),
        (
            "Il y a dans {title} une maîtrise rare, autant dans la forme que dans le fond. "
            "L'œuvre transforme {aspects} en véritable moteur émotionnel, sans jamais donner l'impression de forcer. "
            "La progression est fluide, les personnages existent vraiment, et la conclusion donne du poids à tout ce qui précède. "
            "C'est exactement le type de titre qui rend une plateforme de critiques intéressante, parce qu'il donne envie d'en débattre longuement."
        ),
    ],
}

COMMENT_TEMPLATES = [
    "Je te rejoins sur {aspect}, c'est clairement ce qui m'a le plus marqué aussi.",
    "Ton avis est intéressant, même si j'aurais été un peu plus généreux avec la note.",
    "Je n'avais pas pensé à {aspect} sous cet angle, mais ton argument se défend bien.",
    "La comparaison entre le rythme et les personnages est pertinente, surtout pour {title}.",
    "Je suis d'accord sur l'ambiance, mais j'ai trouvé la fin plus forte que toi.",
    "Ce commentaire me donne envie de revoir l'œuvre en faisant plus attention aux détails.",
    "Je partage ton ressenti : ce n'est pas seulement beau, c'est aussi bien construit.",
    "Je suis plus réservé sur le scénario, mais la réalisation compense beaucoup.",
    "Tu as bien résumé le problème principal : l'idée est bonne, mais tout ne suit pas.",
    "Pour moi, {title} gagne surtout grâce à ses personnages et à son atmosphère.",
    "Je pensais être le seul à avoir remarqué ce souci de rythme.",
    "Très bonne critique, elle explique clairement pourquoi la note est justifiée.",
    "Je mettrais une note différente, mais je comprends totalement ton point de vue.",
    "Le passage sur {aspect} est le plus convaincant de ton analyse.",
    "Ce genre de critique aide vraiment à décider si l'œuvre vaut le détour.",
    "J'ai ressenti la même chose, surtout dans les derniers épisodes ou dernières scènes.",
    "L'œuvre a des défauts, mais elle reste difficile à oublier.",
    "Ton avis nuance bien les qualités et les limites, c'est plus utile qu'une simple note.",
    "Je trouve aussi que {studio} a donné une vraie personnalité visuelle à l'ensemble.",
    "C'est exactement le type de débat qu'on devrait avoir plus souvent sur cette plateforme.",
]

FALLBACK_STUDIOS = ["le studio d'animation", "l'équipe artistique", "la production"]


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError(
            "Cette option doit être un entier supérieur ou égal à 1."
        )
    return number


def non_negative_int(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError(
            "Cette option doit être un entier supérieur ou égal à 0."
        )
    return number


def non_negative_float(value):
    number = float(value)
    if number < 0:
        raise argparse.ArgumentTypeError(
            "Cette option doit être un nombre supérieur ou égal à 0."
        )
    return number


def compact_text(value):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text


class Command(BaseCommand):
    help = (
        "Importe des anime populaires depuis Jikan/MyAnimeList et génère "
        "des données de présentation riches pour Movie Review."
    )

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=positive_int, default=80)
        parser.add_argument("--pages", type=positive_int, default=None)
        parser.add_argument(
            "--type",
            choices=["all", "tv", "movie"],
            default="all",
            dest="anime_type",
        )
        parser.add_argument(
            "--reviews-per-title",
            type=non_negative_int,
            default=8,
            help="Nombre de critiques générées par œuvre.",
        )
        parser.add_argument(
            "--comments-per-review",
            type=non_negative_int,
            default=2,
            help="Nombre maximum de commentaires générés par critique.",
        )
        parser.add_argument(
            "--comments",
            action="store_true",
            default=True,
            help="Conservé pour compatibilité : les commentaires sont générés par défaut.",
        )
        parser.add_argument(
            "--no-comments",
            action="store_false",
            dest="comments",
            help="Désactive la génération de commentaires.",
        )
        parser.add_argument(
            "--characters",
            action="store_true",
            default=True,
            help="Importe les personnages Jikan comme acteurs. Activé par défaut.",
        )
        parser.add_argument(
            "--no-characters",
            action="store_false",
            dest="characters",
            help="Désactive l'appel Jikan aux personnages et utilise le casting local de secours.",
        )
        parser.add_argument("--clear-mal-data", action="store_true")
        parser.add_argument("--sleep", type=non_negative_float, default=1.1)
        parser.add_argument(
            "--keep-existing-generated-comments",
            action="store_true",
            help="Ne nettoie pas les anciens commentaires générés avant d'en créer de nouveaux.",
        )

    def handle(self, *args, **options):
        self.sleep_seconds = options["sleep"]
        self.last_request_at = None

        if options["clear_mal_data"]:
            self.clear_mal_data()

        users, created_users = self.create_presentation_users()
        requested_reviews = min(options["reviews_per_title"], len(users))
        if options["reviews_per_title"] > len(users):
            self.stdout.write(
                self.style.WARNING(
                    f"Le nombre de critiques par titre est limité à {len(users)}, "
                    "car une seule critique est autorisée par utilisateur et par film."
                )
            )

        anime_items = self.fetch_top_anime(
            limit=options["limit"],
            pages=options["pages"],
            anime_type=options["anime_type"],
        )

        imported_film_ids = []
        created_films = 0

        for position, anime in enumerate(anime_items, start=1):
            try:
                film, was_created = self.import_anime(anime)
                imported_film_ids.append(film.pk)
                created_films += int(was_created)

                character_count = 0
                if options["characters"]:
                    character_count = self.import_characters(anime.get("mal_id"), film)
                if character_count < 3:
                    self.attach_fallback_casting(film, seed=int(anime.get("mal_id") or position))

                self.create_reviews_and_comments(
                    anime=anime,
                    film=film,
                    users=users,
                    reviews_per_title=requested_reviews,
                    with_comments=options["comments"],
                    comments_per_review=options["comments_per_review"],
                    keep_existing_comments=options["keep_existing_generated_comments"],
                )
                self.stdout.write(f"[{position}/{len(anime_items)}] {film.titre}")
            except Exception as exc:
                title = anime.get("title_english") or anime.get("title") or "Titre inconnu"
                self.stdout.write(
                    self.style.ERROR(f"Import ignoré pour « {title} » : {exc}")
                )

        self.print_summary(
            imported_film_ids=imported_film_ids,
            created_films=created_films,
            created_users=created_users,
        )

    def clear_mal_data(self):
        films = Film.objects.filter(affiche__startswith="affiches/mal/")
        poster_names = list(films.values_list("affiche", flat=True))
        deleted_films = films.count()
        films.delete()

        deleted_users, _ = get_user_model().objects.filter(
            username__startswith="mal_user_"
        ).delete()

        for poster_name in poster_names:
            try:
                if poster_name and default_storage.exists(poster_name):
                    default_storage.delete(poster_name)
            except OSError as exc:
                self.stdout.write(
                    self.style.WARNING(
                        f"Impossible de supprimer l'affiche {poster_name} : {exc}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Anciennes données MAL supprimées : {deleted_films} films, "
                f"{deleted_users} comptes générés."
            )
        )

    @transaction.atomic
    def create_presentation_users(self):
        User = get_user_model()
        users = []
        created_count = 0

        self.stdout.write("Création des comptes de présentation...")

        admin, admin_created = User.objects.get_or_create(
            username="demo_admin",
            defaults={
                "email": "demo_admin@example.com",
                "first_name": "Admin",
                "last_name": "Movie Review",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin.email = "demo_admin@example.com"
        admin.first_name = "Admin"
        admin.last_name = "Movie Review"
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password(PASSWORD)
        admin.save()
        created_count += int(admin_created)

        for index, (username, first_name, last_name, _focus, _bias) in enumerate(
            PRESENTATION_USERS,
            start=1,
        ):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@example.com"},
            )
            user.email = f"{username}@example.com"
            user.first_name = first_name
            user.last_name = last_name
            user.is_staff = False
            user.is_superuser = False
            user.set_password(PASSWORD)
            user.save()
            users.append(user)
            created_count += int(created)

        return users, created_count

    def fetch_top_anime(self, limit, pages, anime_type):
        page_count = pages or math.ceil(limit / 25)
        anime_items = []
        seen_ids = set()

        self.stdout.write(
            f"Récupération de {limit} titres Jikan sur au plus {page_count} page(s)..."
        )
        for page_number in range(1, page_count + 1):
            remaining = limit - len(anime_items)
            if remaining <= 0:
                break

            params = {
                "page": page_number,
                "limit": min(25, remaining),
                "sfw": "true",
            }
            if anime_type != "all":
                params["type"] = anime_type

            payload = self.fetch_json(f"{JIKAN_API_URL}/top/anime", params=params)
            if not payload:
                continue

            page_items = payload.get("data")
            if not isinstance(page_items, list):
                self.stdout.write(
                    self.style.WARNING(
                        f"Réponse Jikan invalide pour la page {page_number}."
                    )
                )
                continue

            for anime in page_items:
                mal_id = anime.get("mal_id")
                if not mal_id or mal_id in seen_ids:
                    continue
                seen_ids.add(mal_id)
                anime_items.append(anime)
                if len(anime_items) >= limit:
                    break

        if not anime_items:
            self.stdout.write(self.style.WARNING("Aucun titre n'a pu être récupéré."))

        return anime_items

    def fetch_json(self, url, params=None):
        if params:
            url = f"{url}?{parse.urlencode(params)}"

        raw_data = self.fetch_url(url)
        if raw_data is None:
            return None

        try:
            return json.loads(raw_data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.stdout.write(
                self.style.ERROR(f"Réponse JSON invalide pour {url} : {exc}")
            )
            return None

    def fetch_url(self, url):
        for attempt in range(3):
            self.wait_before_request()
            http_request = request.Request(
                url,
                headers={
                    "Accept": "application/json,image/*;q=0.9,*/*;q=0.8",
                    "User-Agent": "MovieReviewDjangoSeed/2.0",
                },
            )
            self.last_request_at = time.monotonic()

            try:
                with request.urlopen(http_request, timeout=30) as response:
                    return response.read()
            except error.HTTPError as exc:
                if exc.code == 429 and attempt < 2:
                    delay = max(3.0, self.sleep_seconds * 2)
                    self.stdout.write(
                        self.style.WARNING(
                            f"Limite Jikan atteinte, nouvelle tentative dans {delay:.1f}s."
                        )
                    )
                    time.sleep(delay)
                    continue
                self.stdout.write(
                    self.style.ERROR(f"Erreur HTTP {exc.code} pour {url}.")
                )
            except (error.URLError, TimeoutError, OSError) as exc:
                if attempt < 2:
                    time.sleep(max(1.5, self.sleep_seconds))
                    continue
                self.stdout.write(
                    self.style.ERROR(f"Erreur réseau pour {url} : {exc}")
                )
            break

        return None

    def wait_before_request(self):
        if self.last_request_at is None:
            return

        elapsed = time.monotonic() - self.last_request_at
        remaining = self.sleep_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def import_anime(self, anime):
        mal_id = anime.get("mal_id")
        if not mal_id:
            raise ValueError("identifiant MAL absent")

        title = self.get_title(anime)
        synopsis = self.build_synopsis(anime)
        genre_name = self.get_primary_genre(anime)
        release_date = self.get_release_date(anime)
        duration = self.parse_duration(anime.get("duration"))
        poster_path = f"affiches/mal/{mal_id}.jpg"

        genre, _ = Genre.objects.get_or_create(nom=genre_name)
        film = Film.objects.filter(affiche=poster_path).first()
        if film is None:
            film = Film.objects.filter(titre=title, date_sortie=release_date).first()

        created = film is None
        if created:
            film = Film.objects.create(
                titre=title,
                synopsis=synopsis,
                genre=genre,
                date_sortie=release_date,
                duree_minutes=duration,
            )
        else:
            film.titre = title
            film.synopsis = synopsis
            film.genre = genre
            film.date_sortie = release_date
            film.duree_minutes = duration
            film.save(
                update_fields=[
                    "titre",
                    "synopsis",
                    "genre",
                    "date_sortie",
                    "duree_minutes",
                ]
            )

        self.attach_poster(anime, film, poster_path)
        return film, created

    def get_title(self, anime):
        title = anime.get("title_english") or anime.get("title") or anime.get("title_japanese") or "Sans titre"
        return compact_text(title)[:200]

    def build_synopsis(self, anime):
        synopsis = compact_text(anime.get("synopsis")) or DEFAULT_SYNOPSIS
        synopsis = re.sub(r"\[Written by MAL Rewrite\]", "", synopsis).strip()
        synopsis = re.sub(r"\(Source:.*?\)", "", synopsis).strip()

        genres = self.get_names(anime, "genres")
        themes = self.get_names(anime, "themes")
        demographics = self.get_names(anime, "demographics")
        studios = self.get_names(anime, "studios")
        score = anime.get("score")
        rank = anime.get("rank")
        members = anime.get("members")

        metadata = []
        if genres:
            metadata.append(f"Genres MAL : {', '.join(genres[:4])}")
        if themes:
            metadata.append(f"Thèmes : {', '.join(themes[:4])}")
        if demographics:
            metadata.append(f"Public : {', '.join(demographics[:3])}")
        if studios:
            metadata.append(f"Studio : {', '.join(studios[:3])}")
        if score:
            metadata.append(f"Score MyAnimeList : {score}/10")
        if rank:
            metadata.append(f"Rang MAL : #{rank}")
        if members:
            metadata.append(f"Popularité : {members} membres MAL")

        if metadata:
            synopsis = f"{synopsis}\n\nDonnées importées pour la démonstration : {' · '.join(metadata)}."

        return synopsis

    def attach_poster(self, anime, film, poster_path):
        if default_storage.exists(poster_path):
            if film.affiche.name != poster_path:
                film.affiche = poster_path
                film.save(update_fields=["affiche"])
            return

        images = anime.get("images") or {}
        jpg_images = images.get("jpg") or {}
        webp_images = images.get("webp") or {}
        poster_url = (
            jpg_images.get("large_image_url")
            or jpg_images.get("image_url")
            or webp_images.get("large_image_url")
            or webp_images.get("image_url")
        )
        if not poster_url:
            self.stdout.write(
                self.style.WARNING(f"Aucune affiche disponible pour {film.titre}.")
            )
            return

        poster_data = self.fetch_url(poster_url)
        if poster_data is None:
            return

        saved_path = default_storage.save(poster_path, ContentFile(poster_data))
        film.affiche = saved_path
        film.save(update_fields=["affiche"])

    def import_characters(self, mal_id, film):
        if not mal_id:
            return 0

        payload = self.fetch_json(f"{JIKAN_API_URL}/anime/{mal_id}/characters")
        if not payload:
            return 0

        character_items = payload.get("data")
        if not isinstance(character_items, list):
            return 0

        created_links = 0
        for item in character_items[:6]:
            character = item.get("character") or {}
            name = compact_text(character.get("name"))[:150]
            if not name:
                continue

            actor, _ = Acteur.objects.get_or_create(nom=name)
            _casting, linked = Casting.objects.get_or_create(film=film, acteur=actor)
            created_links += int(linked)

        return created_links

    def attach_fallback_casting(self, film, seed):
        if Casting.objects.filter(film=film).count() >= 3:
            return

        start = seed % len(DEMO_ACTEURS)
        selected_names = [
            DEMO_ACTEURS[(start + offset) % len(DEMO_ACTEURS)]
            for offset in range(4)
        ]
        for name in selected_names:
            actor, _ = Acteur.objects.get_or_create(nom=name[:150])
            Casting.objects.get_or_create(film=film, acteur=actor)

    def create_reviews_and_comments(
        self,
        anime,
        film,
        users,
        reviews_per_title,
        with_comments,
        comments_per_review,
        keep_existing_comments,
    ):
        if reviews_per_title <= 0:
            return

        mal_id = int(anime.get("mal_id") or film.pk)
        base_score = self.get_local_score(anime)
        aspects = self.get_review_aspects(anime)
        genre = self.get_primary_genre(anime)
        studio = self.get_primary_studio(anime)
        release_year = self.get_release_date(anime).year
        format_label = self.get_format_label(anime)

        for review_index in range(reviews_per_title):
            user = users[(mal_id + review_index) % len(users)]
            persona = PRESENTATION_USERS[(mal_id + review_index) % len(PRESENTATION_USERS)]
            _username, _first_name, _last_name, persona_focus, bias = persona
            note = self.compute_note(base_score, bias, mal_id, review_index)
            title = self.render_review_title(note, mal_id, review_index)
            text = self.render_review_body(
                note=note,
                anime=anime,
                film=film,
                mal_id=mal_id,
                review_index=review_index,
                aspects=aspects,
                genre=genre,
                studio=studio,
                release_year=release_year,
                format_label=format_label,
                persona_focus=persona_focus,
            )

            critique, _created = Critique.objects.update_or_create(
                film=film,
                utilisateur=user,
                defaults={
                    "titre": title,
                    "texte": text,
                    "note": note,
                },
            )

            if with_comments and comments_per_review > 0:
                self.create_comments(
                    critique=critique,
                    users=users,
                    anime=anime,
                    mal_id=mal_id,
                    review_index=review_index,
                    comments_per_review=comments_per_review,
                    aspects=aspects,
                    studio=studio,
                    keep_existing_comments=keep_existing_comments,
                )

    def create_comments(
        self,
        critique,
        users,
        anime,
        mal_id,
        review_index,
        comments_per_review,
        aspects,
        studio,
        keep_existing_comments,
    ):
        if not keep_existing_comments:
            Commentaire.objects.filter(
                critique=critique,
                utilisateur__username__startswith="mal_user_",
            ).delete()

        title = self.get_title(anime)
        aspect = aspects[(mal_id + review_index) % len(aspects)]
        count = 1 + ((mal_id + review_index) % max(1, comments_per_review))

        for offset in range(count):
            commenter = users[(mal_id + review_index + offset + 5) % len(users)]
            if commenter == critique.utilisateur:
                commenter = users[(mal_id + review_index + offset + 6) % len(users)]

            template = COMMENT_TEMPLATES[
                (mal_id + review_index * 3 + offset) % len(COMMENT_TEMPLATES)
            ]
            text = template.format(title=title, aspect=aspect, studio=studio).strip()
            if not text:
                text = DEMO_COMMENTAIRES[(mal_id + offset) % len(DEMO_COMMENTAIRES)]

            Commentaire.objects.get_or_create(
                critique=critique,
                utilisateur=commenter,
                texte=text,
            )

    def render_review_title(self, note, mal_id, review_index):
        choices = REVIEW_TITLES[note]
        return choices[(mal_id + review_index) % len(choices)]

    def render_review_body(
        self,
        note,
        anime,
        film,
        mal_id,
        review_index,
        aspects,
        genre,
        studio,
        release_year,
        format_label,
        persona_focus,
    ):
        templates = REVIEW_BODIES[note]
        template = templates[(mal_id + review_index) % len(templates)]
        selected_aspects = self.human_join(
            [
                aspects[(mal_id + review_index) % len(aspects)],
                aspects[(mal_id + review_index + 1) % len(aspects)],
                persona_focus,
            ]
        )
        score = anime.get("score")
        score_label = f"{score}/10" if score else "non renseigné"
        return template.format(
            title=film.titre,
            aspects=selected_aspects,
            genre=genre,
            studio=studio,
            release_year=release_year,
            format_label=format_label,
            duration=film.duree_minutes,
            score_label=score_label,
            persona_focus=persona_focus,
        )

    def compute_note(self, base_score, bias, mal_id, review_index):
        variations = [-0.55, -0.30, -0.10, 0.10, 0.25, 0.45]
        variation = variations[(mal_id + review_index) % len(variations)]
        raw_note = base_score + bias + variation
        return max(1, min(5, int(raw_note + 0.5)))

    def get_local_score(self, anime):
        score = anime.get("score")
        try:
            value = float(score) / 2
        except (TypeError, ValueError):
            value = 3.0
        return max(1.0, min(5.0, value))

    def get_primary_genre(self, anime):
        genres = anime.get("genres") or []
        if genres and isinstance(genres[0], dict):
            name = compact_text(genres[0].get("name"))
            if name:
                return name[:100]
        return "Animation"

    def get_primary_studio(self, anime):
        studios = self.get_names(anime, "studios")
        if studios:
            return studios[0]
        mal_id = int(anime.get("mal_id") or 0)
        return FALLBACK_STUDIOS[mal_id % len(FALLBACK_STUDIOS)]

    def get_review_aspects(self, anime):
        aspects = []
        for name in self.get_names(anime, "genres") + self.get_names(anime, "themes"):
            aspects.extend(GENRE_ASPECTS.get(name, []))
        if not aspects:
            aspects.extend(
                [
                    "le rythme général",
                    "l'écriture des personnages",
                    "l'ambiance visuelle",
                    "la progression émotionnelle",
                ]
            )
        return list(dict.fromkeys(aspects))[:8]

    def get_format_label(self, anime):
        anime_type = compact_text(anime.get("type")) or "format animé"
        episodes = anime.get("episodes")
        if episodes:
            return f"{anime_type} en {episodes} épisode{'s' if episodes != 1 else ''}"
        return anime_type

    def get_names(self, anime, key):
        items = anime.get(key) or []
        names = []
        for item in items:
            if isinstance(item, dict):
                name = compact_text(item.get("name"))
                if name:
                    names.append(name)
        return names

    def get_release_date(self, anime):
        aired = anime.get("aired") or {}
        aired_from = aired.get("from")
        if isinstance(aired_from, str):
            try:
                return date.fromisoformat(aired_from[:10])
            except ValueError:
                pass

        try:
            year = int(anime.get("year"))
            if 1 <= year <= 9999:
                return date(year, 1, 1)
        except (TypeError, ValueError):
            pass

        return date(2000, 1, 1)

    def parse_duration(self, duration):
        if not duration:
            return 90

        text = str(duration).lower()
        hours_match = re.search(r"(\d+)\s*(?:hr|hour)", text)
        minutes_match = re.search(r"(\d+)\s*(?:min|minute)", text)
        hours = int(hours_match.group(1)) if hours_match else 0
        minutes = int(minutes_match.group(1)) if minutes_match else 0
        total = hours * 60 + minutes
        return total if total > 0 else 90

    def human_join(self, values):
        cleaned = []
        for value in values:
            value = compact_text(value)
            if value and value not in cleaned:
                cleaned.append(value)
        if not cleaned:
            return "la mise en scène et les personnages"
        if len(cleaned) == 1:
            return cleaned[0]
        return f"{', '.join(cleaned[:-1])} et {cleaned[-1]}"

    def print_summary(self, imported_film_ids, created_films, created_users):
        unique_film_ids = list(set(imported_film_ids))
        genres = Genre.objects.filter(films__id__in=unique_film_ids).distinct().count()
        actors = Acteur.objects.filter(films__id__in=unique_film_ids).distinct().count()
        reviews = Critique.objects.filter(film_id__in=unique_film_ids).count()
        comments = Commentaire.objects.filter(
            critique__film_id__in=unique_film_ids
        ).count()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Import Jikan enrichi terminé."))
        self.stdout.write(
            f"Films importés ou mis à jour : {len(unique_film_ids)} "
            f"({created_films} créés)"
        )
        self.stdout.write(f"Genres liés : {genres}")
        self.stdout.write(f"Acteurs/personnages liés : {actors}")
        self.stdout.write(f"Critiques générées : {reviews}")
        self.stdout.write(f"Commentaires générés : {comments}")
        self.stdout.write(
            f"Comptes de test : demo_admin + 25 mal_user_* "
            f"({created_users} nouveaux), mot de passe : {PASSWORD}"
        )