from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from movies.models import Film


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".svg"}


class Command(BaseCommand):
    help = "Associe des affiches locales aux films de démo depuis media/affiches/local/."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all-films",
            action="store_true",
            help="Associe les affiches à tous les films, pas seulement aux films de démo.",
        )

    def handle(self, *args, **options):
        posters_dir = Path(settings.MEDIA_ROOT) / "affiches" / "local"

        if not posters_dir.exists():
            self.stderr.write(
                self.style.ERROR(
                    f"Dossier introuvable : {posters_dir}\n"
                    "Crée-le puis copie tes images dedans."
                )
            )
            return

        image_paths = sorted(
            path for path in posters_dir.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )

        if not image_paths:
            self.stderr.write(
                self.style.ERROR(
                    f"Aucune image trouvée dans {posters_dir}.\n"
                    "Formats acceptés : jpg, jpeg, png, webp, svg."
                )
            )
            return

        if options["all_films"]:
            films = list(Film.objects.order_by("titre"))
        else:
            films = list(Film.objects.filter(titre__startswith="Démo —").order_by("titre"))

        if not films:
            self.stderr.write(self.style.ERROR("Aucun film trouvé à mettre à jour."))
            return

        updated_count = 0

        for index, film in enumerate(films):
            image_path = image_paths[index % len(image_paths)]
            relative_path = f"affiches/local/{image_path.name}"

            film.affiche.name = relative_path
            film.save(update_fields=["affiche"])

            updated_count += 1
            self.stdout.write(f"{film.titre} -> {relative_path}")

        self.stdout.write(
            self.style.SUCCESS(
                f"{updated_count} film(s) mis à jour avec des affiches locales."
            )
        )