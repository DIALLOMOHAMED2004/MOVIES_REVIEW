from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Avg, Count, Q


class Genre(models.Model):
    # Modèle représentant une catégorie de film.
    #
    # Exemple :
    # - Action ;
    # - Drame ;
    # - Comédie ;
    # - Science-fiction.
    #
    # Un film est associé à un seul genre via une relation ForeignKey
    # définie plus bas dans le modèle Film.
    nom = models.CharField(
        # Longueur maximale autorisée pour le nom du genre.
        max_length=100,

        # Empêche deux genres d'avoir exactement le même nom.
        #
        # Cette contrainte évite les doublons du type :
        # - "Drame" ;
        # - "Drame".
        unique=True,

        # Nom lisible affiché dans l'admin Django et les formulaires.
        verbose_name="Nom du genre"
    )

    class Meta:
        # Trie les genres par ordre alphabétique par défaut.
        #
        # Cela s'applique notamment aux QuerySets si aucun autre tri
        # n'est explicitement défini.
        ordering = ["nom"]

        # Nom singulier affiché dans l'admin Django.
        verbose_name = "Genre"

        # Nom pluriel affiché dans l'admin Django.
        verbose_name_plural = "Genres"

    def __str__(self):
        # Représentation textuelle d'un genre.
        #
        # Cette méthode est utilisée automatiquement par Django :
        # - dans l'admin ;
        # - dans les menus déroulants ;
        # - dans le shell ;
        # - dans les templates si l'objet est affiché directement.
        return self.nom


class Acteur(models.Model):
    # Modèle représentant un acteur pouvant être associé à un ou plusieurs films.
    #
    # La relation entre Film et Acteur passe par le modèle intermédiaire Casting,
    # ce qui permet de contrôler explicitement les associations.
    nom = models.CharField(
        # Longueur maximale du nom de l'acteur.
        max_length=150,

        # Nom lisible affiché dans l'admin et les formulaires.
        verbose_name="Nom de l'acteur"
    )

    class Meta:
        # Trie les acteurs par ordre alphabétique.
        ordering = ["nom"]

        # Nom singulier affiché dans l'interface d'administration.
        verbose_name = "Acteur"

        # Nom pluriel affiché dans l'interface d'administration.
        verbose_name_plural = "Acteurs"

    def __str__(self):
        # Représentation textuelle d'un acteur.
        #
        # Elle permet d'afficher directement son nom lorsqu'un objet Acteur
        # est rendu dans l'admin, un formulaire ou un template.
        return self.nom


class Film(models.Model):
    # Modèle central de l'application.
    #
    # Il représente un film visible dans le catalogue public.
    #
    # Un film possède :
    # - un titre ;
    # - un synopsis ;
    # - un genre ;
    # - une date de sortie ;
    # - une durée ;
    # - éventuellement une affiche ;
    # - un casting principal ;
    # - des statistiques calculées à partir des critiques.
    titre = models.CharField(
        # Longueur maximale du titre.
        max_length=200,

        # Nom lisible affiché dans l'admin et les formulaires.
        verbose_name="Titre"
    )

    synopsis = models.TextField(
        # Texte long décrivant le film.
        verbose_name="Synopsis"
    )

    genre = models.ForeignKey(
        # Modèle cible de la relation.
        Genre,

        # on_delete=models.PROTECT empêche la suppression d'un genre
        # tant qu'il est encore utilisé par au moins un film.
        #
        # Cela évite de laisser des films sans genre valide.
        on_delete=models.PROTECT,

        # Nom de la relation inverse.
        #
        # Grâce à related_name="films", on peut faire :
        # genre.films.all()
        # pour récupérer tous les films associés à un genre.
        related_name="films",

        # Nom lisible du champ.
        verbose_name="Genre"
    )

    date_sortie = models.DateField(
        # Date de sortie officielle ou approximative du film.
        verbose_name="Date de sortie"
    )

    duree_minutes = models.PositiveIntegerField(
        # La durée doit être au minimum de 1 minute.
        #
        # PositiveIntegerField garantit déjà une valeur positive,
        # et MinValueValidator(1) renforce explicitement la règle métier.
        validators=[MinValueValidator(1)],

        # Nom affiché dans l'admin et les formulaires.
        verbose_name="Durée en minutes"
    )

    affiche = models.ImageField(
        # Dossier de stockage relatif dans MEDIA_ROOT.
        #
        # Les affiches uploadées seront placées dans :
        # media/affiches/
        upload_to="affiches/",

        # blank=True autorise le formulaire à être soumis sans affiche.
        blank=True,

        # null=True autorise la base de données à stocker NULL
        # lorsqu'aucune affiche n'est fournie.
        null=True,

        # Nom lisible du champ.
        verbose_name="Affiche du film"
    )

    acteurs = models.ManyToManyField(
        # Modèle cible de la relation many-to-many.
        Acteur,

        # La relation passe par le modèle Casting.
        #
        # Cela permet de gérer explicitement la table intermédiaire
        # au lieu de laisser Django la créer automatiquement.
        through="Casting",

        # Nom de la relation inverse côté Acteur.
        #
        # Grâce à related_name="films", on peut faire :
        # acteur.films.all()
        related_name="films",

        # Nom lisible du champ.
        verbose_name="Casting principal"
    )

    note_moyenne = models.DecimalField(
        # max_digits=3 et decimal_places=2 permettent des valeurs comme :
        # - 4.50 ;
        # - 3.25 ;
        # - 5.00.
        #
        # Le champ est nullable car un film peut ne pas encore avoir de critique.
        max_digits=3,
        decimal_places=2,

        # Autorise le champ à être vide dans les formulaires.
        blank=True,

        # Autorise NULL en base de données.
        null=True,

        # editable=False empêche la modification manuelle dans les ModelForms.
        #
        # La note moyenne est calculée automatiquement à partir des critiques.
        editable=False,

        # Nom lisible du champ.
        verbose_name="Note moyenne"
    )

    nombre_critiques = models.PositiveIntegerField(
        # Valeur initiale pour un film nouvellement créé.
        default=0,

        # Ce champ est calculé automatiquement et ne doit pas être modifié
        # directement via un formulaire.
        editable=False,

        # Nom lisible du champ.
        verbose_name="Nombre de critiques"
    )

    class Meta:
        # Trie les films par titre par défaut.
        ordering = ["titre"]

        # Nom singulier affiché dans l'admin.
        verbose_name = "Film"

        # Nom pluriel affiché dans l'admin.
        verbose_name_plural = "Films"

        # Index de base de données destinés à accélérer certaines requêtes.
        #
        # Ces index sont utiles pour :
        # - les recherches par titre ;
        # - les tris ou filtres par date de sortie ;
        # - les classements par note moyenne ;
        # - les classements par nombre de critiques.
        indexes = [
            models.Index(fields=["titre"]),
            models.Index(fields=["date_sortie"]),
            models.Index(fields=["note_moyenne"]),
            models.Index(fields=["nombre_critiques"]),
        ]

        # Contraintes de base de données.
        #
        # Elles renforcent les règles métier au niveau SQL,
        # même si une erreur ou un contournement survient côté formulaire/vue.
        constraints = [
            models.CheckConstraint(
                # La durée doit toujours être supérieure ou égale à 1.
                condition=Q(duree_minutes__gte=1),
                name="film_duree_positive"
            ),
            models.CheckConstraint(
                # La note moyenne doit être :
                # - comprise entre 0 et 5 ;
                # - ou être NULL si le film n'a pas encore de critique.
                condition=(
                    Q(note_moyenne__gte=0) & Q(note_moyenne__lte=5)
                ) | Q(note_moyenne__isnull=True),
                name="film_note_moyenne_entre_0_et_5"
            ),
        ]

    def __str__(self):
        # Représentation textuelle d'un film.
        #
        # Elle permet d'afficher le titre du film dans l'admin,
        # les formulaires, les relations et les templates.
        return self.titre

    @property
    def annee_sortie(self):
        # Propriété pratique retournant uniquement l'année de sortie du film.
        #
        # Elle permet d'écrire :
        # film.annee_sortie
        #
        # au lieu de :
        # film.date_sortie.year
        #
        # dans les templates ou dans le code Python.
        return self.date_sortie.year

    def afficher_note(self):
        # Retourne une version lisible de la note moyenne du film.
        #
        # Cette méthode est utile dans les templates pour éviter d'écrire
        # la logique d'affichage directement dans le HTML.

        # Si aucune critique n'a encore été publiée,
        # le film n'a pas de note moyenne.
        if self.note_moyenne is None:
            return "Pas encore noté"

        # Si une note moyenne existe, on l'affiche sous la forme "x/5".
        return f"{self.note_moyenne}/5"

    def mettre_a_jour_statistiques(self):
        """
        Met à jour la note moyenne et le nombre de critiques du film.

        Cette méthode respecte la règle du cahier des charges :
        après l'ajout, la modification ou la suppression d'une critique,
        la note moyenne du film doit être mise à jour.
        """

        # Calcule en une seule requête SQL :
        # - la moyenne des notes des critiques du film ;
        # - le nombre total de critiques associées au film.
        #
        # self.critiques fonctionne grâce au related_name="critiques"
        # défini sur la ForeignKey Critique.film.
        statistiques = self.critiques.aggregate(
            moyenne=Avg("note"),
            total=Count("id")
        )

        # Récupère la moyenne calculée.
        moyenne = statistiques["moyenne"]

        # Récupère le nombre total de critiques.
        total = statistiques["total"]

        # Si le film n'a aucune critique,
        # Avg("note") retourne None.
        if moyenne is None:
            nouvelle_moyenne = None
        else:
            # Arrondit la moyenne à deux décimales puis la convertit en Decimal.
            #
            # Decimal est cohérent avec le type DecimalField utilisé en base.
            # str(...) évite certains problèmes de précision des floats.
            nouvelle_moyenne = Decimal(str(round(moyenne, 2)))

        # Met à jour directement la ligne du film en base de données.
        #
        # L'utilisation de update() évite d'appeler save() sur Film,
        # ce qui limite les effets de bord potentiels.
        Film.objects.filter(pk=self.pk).update(
            note_moyenne=nouvelle_moyenne,
            nombre_critiques=total
        )

        # Met aussi à jour l'objet Python courant.
        #
        # Cela permet de disposer immédiatement des nouvelles valeurs
        # sans devoir appeler refresh_from_db().
        self.note_moyenne = nouvelle_moyenne
        self.nombre_critiques = total


class Casting(models.Model):
    # Modèle intermédiaire entre Film et Acteur.
    #
    # Il matérialise la relation many-to-many :
    # - un film peut avoir plusieurs acteurs ;
    # - un acteur peut jouer dans plusieurs films.
    #
    # L'existence explicite de ce modèle permet :
    # - d'ajouter des contraintes personnalisées ;
    # - de gérer facilement les castings depuis l'admin ou le dashboard ;
    # - d'étendre plus tard le casting avec d'autres champs si nécessaire
    #   comme le rôle joué, l'ordre d'affichage, etc.
    film = models.ForeignKey(
        # Film concerné par cette association de casting.
        Film,

        # Si le film est supprimé, ses castings sont supprimés aussi.
        on_delete=models.CASCADE,

        # Relation inverse :
        # film.castings.all()
        related_name="castings",

        # Nom lisible du champ.
        verbose_name="Film"
    )

    acteur = models.ForeignKey(
        # Acteur associé au film.
        Acteur,

        # Si l'acteur est supprimé, ses castings sont supprimés aussi.
        #
        # À noter : certaines vues du dashboard peuvent empêcher la suppression
        # d'un acteur encore utilisé, mais cette règle définit le comportement
        # de base au niveau du modèle.
        on_delete=models.CASCADE,

        # Relation inverse :
        # acteur.castings.all()
        related_name="castings",

        # Nom lisible du champ.
        verbose_name="Acteur"
    )

    class Meta:
        # Nom singulier affiché dans l'admin.
        verbose_name = "Casting"

        # Nom pluriel affiché dans l'admin.
        verbose_name_plural = "Castings"

        # Contraintes de base de données.
        constraints = [
            models.UniqueConstraint(
                # Empêche d'associer plusieurs fois le même acteur au même film.
                #
                # Exemple interdit :
                # - Film A + Acteur X ;
                # - Film A + Acteur X.
                fields=["film", "acteur"],
                name="casting_film_acteur_unique"
            )
        ]

    def __str__(self):
        # Représentation textuelle d'un casting.
        #
        # Exemple :
        # "Camille Durand dans Nuit rouge"
        return f"{self.acteur} dans {self.film}"


class Critique(models.Model):
    # Modèle représentant une critique publiée par un utilisateur sur un film.
    #
    # Une critique contient :
    # - un film concerné ;
    # - un auteur ;
    # - un titre ;
    # - un texte ;
    # - une note de 1 à 5 ;
    # - une date de publication ;
    # - une date de modification.
    #
    # Ce modèle contient aussi une logique importante :
    # lorsqu'une critique est créée, modifiée ou supprimée,
    # les statistiques du film associé sont recalculées.
    film = models.ForeignKey(
        # Film concerné par la critique.
        Film,

        # Si le film est supprimé, ses critiques sont supprimées aussi.
        on_delete=models.CASCADE,

        # Relation inverse :
        # film.critiques.all()
        related_name="critiques",

        # Nom lisible du champ.
        verbose_name="Film concerné"
    )

    utilisateur = models.ForeignKey(
        # Modèle utilisateur actif du projet.
        #
        # settings.AUTH_USER_MODEL est préféré à un import direct de User,
        # car il reste compatible avec un modèle utilisateur personnalisé.
        settings.AUTH_USER_MODEL,

        # Si l'utilisateur est supprimé, ses critiques sont supprimées aussi.
        on_delete=models.CASCADE,

        # Relation inverse :
        # utilisateur.critiques.all()
        related_name="critiques",

        # Nom lisible du champ.
        verbose_name="Auteur"
    )

    titre = models.CharField(
        # Longueur maximale du titre de la critique.
        max_length=200,

        # Nom lisible du champ.
        verbose_name="Titre de la critique"
    )

    texte = models.TextField(
        # Texte complet de la critique.
        verbose_name="Texte de la critique"
    )

    note = models.PositiveSmallIntegerField(
        # La note est limitée entre 1 et 5.
        #
        # Les validators agissent côté Django/formulaire/modèle,
        # tandis que la CheckConstraint plus bas renforce aussi la règle en base.
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ],

        # Nom lisible du champ.
        verbose_name="Note sur 5"
    )

    date_publication = models.DateTimeField(
        # Définit automatiquement la date lors de la création de la critique.
        auto_now_add=True,

        # Nom lisible du champ.
        verbose_name="Date de publication"
    )

    date_modification = models.DateTimeField(
        # Met automatiquement à jour la date à chaque sauvegarde.
        auto_now=True,

        # Nom lisible du champ.
        verbose_name="Date de dernière modification"
    )

    class Meta:
        # Les critiques les plus récentes apparaissent en premier par défaut.
        ordering = ["-date_publication"]

        # Nom singulier affiché dans l'admin.
        verbose_name = "Critique"

        # Nom pluriel affiché dans l'admin.
        verbose_name_plural = "Critiques"

        # Contraintes de base de données.
        constraints = [
            models.UniqueConstraint(
                # Empêche un même utilisateur de publier plusieurs critiques
                # pour un même film.
                #
                # Cette règle correspond à un comportement classique :
                # un utilisateur peut donner un avis par film, puis le modifier
                # s'il souhaite changer son opinion.
                fields=["film", "utilisateur"],
                name="critique_unique_par_utilisateur_et_film"
            ),
            models.CheckConstraint(
                # Renforce au niveau base de données le fait que la note
                # doit être comprise entre 1 et 5.
                condition=Q(note__gte=1) & Q(note__lte=5),
                name="critique_note_entre_1_et_5"
            ),
        ]

    def __str__(self):
        # Représentation textuelle d'une critique.
        #
        # Exemple :
        # "Très réussi - Nuit rouge par alice"
        return f"{self.titre} - {self.film} par {self.utilisateur}"

    def save(self, **kwargs):
        # Surcharge de la méthode save().
        #
        # Son objectif est de garantir que les statistiques du film sont toujours
        # cohérentes après la création ou la modification d'une critique.
        #
        # Cas gérés :
        # - création d'une nouvelle critique ;
        # - modification d'une critique existante ;
        # - éventuel changement du film associé à une critique.
        ancien_film_id = None

        # Si self.pk existe, cela signifie que la critique existe déjà en base.
        #
        # On récupère alors l'ancien film associé avant la sauvegarde.
        # C'est utile si la critique est déplacée d'un film vers un autre.
        if self.pk:
            ancien_film_id = (
                Critique.objects
                .filter(pk=self.pk)
                .values_list("film_id", flat=True)
                .first()
            )

        # Exécute la sauvegarde normale de Django.
        #
        # Après cet appel :
        # - la critique est créée ou modifiée en base ;
        # - self.film_id correspond au film actuel.
        super().save(**kwargs)

        # Recalcule les statistiques du film actuellement associé à la critique.
        self.film.mettre_a_jour_statistiques()

        # Si la critique existait déjà et que son film a changé,
        # il faut aussi recalculer les statistiques de l'ancien film.
        #
        # Exemple :
        # une critique était associée à Film A puis déplacée vers Film B.
        # Film B doit être recalculé, mais Film A aussi,
        # car il vient de perdre une critique.
        if ancien_film_id and ancien_film_id != self.film_id:
            ancien_film = Film.objects.filter(pk=ancien_film_id).first()

            # Si l'ancien film existe toujours, on met ses statistiques à jour.
            if ancien_film:
                ancien_film.mettre_a_jour_statistiques()

    def delete(self, using=None, keep_parents=False):
        # Surcharge de la méthode delete().
        #
        # Son objectif est de recalculer les statistiques du film
        # après suppression d'une critique.
        #
        # Sans cette méthode, le film pourrait conserver :
        # - une note moyenne incorrecte ;
        # - un nombre de critiques incorrect.

        # On garde une référence au film avant de supprimer la critique.
        #
        # Après suppression, self.film pourrait ne plus être fiable
        # selon le contexte d'exécution.
        film = self.film

        # Exécute la suppression standard de Django.
        resultat = super().delete(using=using, keep_parents=keep_parents)

        # Recalcule les statistiques du film après suppression de la critique.
        film.mettre_a_jour_statistiques()

        # Retourne le résultat standard de delete().
        return resultat


class Commentaire(models.Model):
    # Modèle représentant un commentaire publié sur une critique.
    #
    # Un commentaire est lié :
    # - à une critique ;
    # - à un utilisateur ;
    # - à un texte ;
    # - à une date de publication.
    #
    # Contrairement à Critique, ce modèle ne recalcule pas les statistiques du film,
    # car les commentaires n'influencent pas la note moyenne.
    critique = models.ForeignKey(
        # Critique concernée par le commentaire.
        Critique,

        # Si la critique est supprimée, ses commentaires disparaissent aussi.
        on_delete=models.CASCADE,

        # Relation inverse :
        # critique.commentaires.all()
        related_name="commentaires",

        # Nom lisible du champ.
        verbose_name="Critique concernée"
    )

    utilisateur = models.ForeignKey(
        # Auteur du commentaire.
        settings.AUTH_USER_MODEL,

        # Si l'utilisateur est supprimé, ses commentaires sont supprimés aussi.
        on_delete=models.CASCADE,

        # Relation inverse :
        # utilisateur.commentaires.all()
        related_name="commentaires",

        # Nom lisible du champ.
        verbose_name="Auteur"
    )

    texte = models.TextField(
        # Contenu complet du commentaire.
        verbose_name="Texte du commentaire"
    )

    date_publication = models.DateTimeField(
        # Date automatiquement définie à la création du commentaire.
        auto_now_add=True,

        # Nom lisible du champ.
        verbose_name="Date de publication"
    )

    class Meta:
        # Trie les commentaires du plus ancien au plus récent.
        #
        # Cela est pratique pour afficher une discussion dans l'ordre naturel
        # de publication sous une critique.
        ordering = ["date_publication"]

        # Nom singulier affiché dans l'admin.
        verbose_name = "Commentaire"

        # Nom pluriel affiché dans l'admin.
        verbose_name_plural = "Commentaires"

    def __str__(self):
        # Représentation textuelle d'un commentaire.
        #
        # Exemple :
        # "Commentaire de alice sur Très réussi - Nuit rouge par alice"
        return f"Commentaire de {self.utilisateur} sur {self.critique}"