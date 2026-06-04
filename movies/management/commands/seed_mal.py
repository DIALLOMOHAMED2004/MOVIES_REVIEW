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

from movies.models import Acteur, Casting, Commentaire, Critique, Film, Genre


JIKAN_API_URL = "https://api.jikan.moe/v4"
PASSWORD = "DemoPass123!"
DEFAULT_SYNOPSIS = (
    "Synopsis indisponible. Cette œuvre d'animation est importée depuis "
    "MyAnimeList afin d'alimenter la démonstration Movie Review."
)

CRITIQUE_TITRES = {
    1: "Une œuvre qui peine à convaincre",
    2: "De bonnes idées, mais un résultat inégal",
    3: "Une expérience plaisante malgré quelques défauts",
    4: "Une très belle réussite",
    5: "Une œuvre remarquable et mémorable",
}

CRITIQUE_TEXTES = {
    1: (
        "Malgré un univers prometteur, le rythme manque de maîtrise et les "
        "personnages restent trop peu développés. Quelques scènes fonctionnent, "
        "mais l'ensemble ne parvient pas vraiment à maintenir l'intérêt."
    ),
    2: (
        "La proposition possède de vraies qualités visuelles et plusieurs idées "
        "intéressantes. Le récit reste toutefois irrégulier, avec des passages "
        "réussis et d'autres beaucoup moins convaincants."
    ),
    3: (
        "L'ensemble est agréable à suivre et propose des personnages attachants. "
        "Le scénario reste parfois prévisible, mais l'ambiance et la réalisation "
        "offrent un divertissement solide."
    ),
    4: (
        "La mise en scène, le rythme et le développement des personnages forment "
        "un ensemble très réussi. L'œuvre sait créer de l'émotion tout en gardant "
        "une identité visuelle forte."
    ),
    5: (
        "Une œuvre particulièrement maîtrisée, portée par une narration forte, "
        "des personnages marquants et une réalisation inspirée. Une expérience "
        "qui reste longtemps en mémoire."
    ),
}

COMMENTAIRES = [
    "Je partage cet avis, surtout concernant le développement des personnages.",
    "Ton analyse du rythme est juste et bien expliquée.",
    "Je suis un peu moins sévère, mais les arguments sont convaincants.",
    "Cette critique résume très bien mon ressenti après le visionnage.",
    "La réalisation est effectivement l'un des grands points forts de cette œuvre.",
    "J'avais un avis différent, mais ce point de vue est intéressant.",
]


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


class Command(BaseCommand):
    help = "Importe des anime populaires depuis Jikan et génère des avis fictifs."

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
            default=5,
        )
        parser.add_argument("--comments", action="store_true")
        parser.add_argument("--characters", action="store_true")
        parser.add_argument("--clear-mal-data", action="store_true")
        parser.add_argument("--sleep", type=non_negative_float, default=0.8)

    def handle(self, *args, **options):
        self.sleep_seconds = options["sleep"]
        self.last_request_at = None

        if options["clear_mal_data"]:
            self.clear_mal_data()

        users, created_users = self.create_test_users()
        requested_reviews = min(options["reviews_per_title"], len(users))
        if options["reviews_per_title"] > len(users):
            self.stdout.write(
                self.style.WARNING(
                    "Le nombre de critiques par titre est limité à 25, car une "
                    "seule critique est autorisée par utilisateur et par film."
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
                created_films += int(was_created)
                imported_film_ids.append(film.pk)

                if options["characters"]:
                    self.import_characters(anime.get("mal_id"), film)

                self.create_reviews(
                    anime=anime,
                    film=film,
                    users=users,
                    reviews_per_title=requested_reviews,
                    with_comments=options["comments"],
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
            self.style.SUCCESS(f"Anciennes données MAL supprimées : {deleted_films} films.")
        )

    def create_test_users(self):
        User = get_user_model()
        users = []
        created_count = 0

        self.stdout.write("Création des comptes fictifs MAL...")
        for index in range(1, 26):
            username = f"mal_user_{index:02d}"
            user, created = User.objects.get_or_create(username=username)
            user.set_password(PASSWORD)
            user.save(update_fields=["password"])
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
        for attempt in range(2):
            self.wait_before_request()
            http_request = request.Request(
                url,
                headers={
                    "Accept": "application/json,image/*;q=0.9,*/*;q=0.8",
                    "User-Agent": "MovieReviewDjangoSeed/1.0",
                },
            )
            self.last_request_at = time.monotonic()

            try:
                with request.urlopen(http_request, timeout=30) as response:
                    return response.read()
            except error.HTTPError as exc:
                if exc.code == 429 and attempt == 0:
                    delay = max(2.0, self.sleep_seconds)
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

        title = (anime.get("title_english") or anime.get("title") or "Sans titre")[:200]
        synopsis = anime.get("synopsis") or DEFAULT_SYNOPSIS
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

    def attach_poster(self, anime, film, poster_path):
        if default_storage.exists(poster_path):
            if film.affiche.name != poster_path:
                film.affiche = poster_path
                film.save(update_fields=["affiche"])
            return

        images = anime.get("images") or {}
        jpg_images = images.get("jpg") or {}
        poster_url = jpg_images.get("large_image_url") or jpg_images.get("image_url")
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
            return

        payload = self.fetch_json(f"{JIKAN_API_URL}/anime/{mal_id}/characters")
        if not payload:
            return

        character_items = payload.get("data")
        if not isinstance(character_items, list):
            return

        for item in character_items[:5]:
            character = item.get("character") or {}
            name = str(character.get("name") or "").strip()[:150]
            if not name:
                continue

            actor = Acteur.objects.filter(nom=name).first()
            if actor is None:
                actor = Acteur.objects.create(nom=name)
            Casting.objects.get_or_create(film=film, acteur=actor)

    def create_reviews(
        self,
        anime,
        film,
        users,
        reviews_per_title,
        with_comments,
    ):
        mal_id = int(anime.get("mal_id") or 0)
        score = anime.get("score")
        try:
            local_score = float(score) / 2
        except (TypeError, ValueError):
            local_score = 3.0

        variations = [-0.6, -0.3, 0.0, 0.3, 0.6]
        for review_index in range(reviews_per_title):
            user_index = (mal_id + review_index) % len(users)
            user = users[user_index]
            variation = variations[(mal_id + review_index) % len(variations)]
            note = max(1, min(5, int(local_score + variation + 0.5)))

            critique, _ = Critique.objects.get_or_create(
                film=film,
                utilisateur=user,
                defaults={
                    "titre": CRITIQUE_TITRES[note],
                    "texte": CRITIQUE_TEXTES[note],
                    "note": note,
                },
            )

            if with_comments:
                self.create_comments(
                    critique=critique,
                    users=users,
                    user_index=user_index,
                    seed=mal_id + review_index,
                )

    def create_comments(self, critique, users, user_index, seed):
        if seed % 2:
            return

        comment_count = 2 if seed % 5 == 0 else 1
        for offset in range(comment_count):
            commenter = users[(user_index + offset + 7) % len(users)]
            text = COMMENTAIRES[(seed + offset) % len(COMMENTAIRES)].strip()
            if not text:
                continue
            Commentaire.objects.get_or_create(
                critique=critique,
                utilisateur=commenter,
                texte=text,
            )

    def get_primary_genre(self, anime):
        genres = anime.get("genres") or []
        if genres and isinstance(genres[0], dict):
            name = str(genres[0].get("name") or "").strip()
            if name:
                return name[:100]
        return "Animation"

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

    def print_summary(self, imported_film_ids, created_films, created_users):
        unique_film_ids = list(set(imported_film_ids))
        genres = Genre.objects.filter(films__id__in=unique_film_ids).distinct().count()
        actors = Acteur.objects.filter(films__id__in=unique_film_ids).distinct().count()
        reviews = Critique.objects.filter(film_id__in=unique_film_ids).count()
        comments = Commentaire.objects.filter(
            critique__film_id__in=unique_film_ids
        ).count()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Import Jikan terminé."))
        self.stdout.write(
            f"Films importés ou récupérés : {len(unique_film_ids)} "
            f"({created_films} créés)"
        )
        self.stdout.write(f"Genres liés : {genres}")
        self.stdout.write(f"Acteurs/personnages liés : {actors}")
        self.stdout.write(f"Critiques fictives : {reviews}")
        self.stdout.write(f"Commentaires fictifs : {comments}")
        self.stdout.write(
            f"Comptes de test : 25 disponibles ({created_users} créés), "
            f"mot de passe : {PASSWORD}"
        )
