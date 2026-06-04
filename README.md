# Movie Review

Movie Review est une application Django de découverte et de critique de films.
Elle permet de consulter un catalogue, publier une critique notée, commenter les
avis de la communauté et explorer les films les mieux notés ou les plus
populaires. Un dashboard réservé au staff complète l'administration Django
standard pour la gestion et la modération.

## Fonctionnalités principales

- Catalogue de films filtrable par genre, année et note minimale.
- Détail d'un film avec synopsis, casting, critiques et commentaires.
- Inscription, connexion par nom d'utilisateur ou email, profil et réinitialisation
  du mot de passe.
- Une critique maximum par utilisateur et par film.
- Modification et suppression réservées à l'auteur de la critique.
- Calcul automatique de la note moyenne et du nombre de critiques.
- Classements par note moyenne et popularité.
- Gestion des films, genres, acteurs et castings.
- Modération des critiques et commentaires via Django Admin ou le dashboard.

## Technologies

- Python 3.12
- Django 6.0
- PostgreSQL
- Django Templates, HTML et CSS
- Pillow pour les affiches
- `python-dotenv` pour les variables d'environnement

## Prérequis

- Python 3.12 ou version compatible avec Django 6.0
- PostgreSQL accessible localement ou à distance
- `venv` et `pip`

## Installation

```bash
git clone <url-du-depot>
cd MOVIES_REVIEW

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Copier ensuite l'exemple de configuration et remplacer les valeurs locales :

```bash
cp .env.example .env
```

Générer une clé Django adaptée :

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

Reporter la valeur générée dans `SECRET_KEY` du fichier `.env`. Ne jamais
committer `.env` ni une véritable clé de production.

## Configuration PostgreSQL

Exemple de création d'une base et d'un utilisateur avec `psql` :

```sql
CREATE DATABASE movie_review;
CREATE USER movie_review WITH PASSWORD 'mot-de-passe-local';
GRANT ALL PRIVILEGES ON DATABASE movie_review TO movie_review;
```

Adapter ensuite les variables `POSTGRES_*` dans `.env` :

```dotenv
POSTGRES_DB=movie_review
POSTGRES_USER=movie_review
POSTGRES_PASSWORD=mot-de-passe-local
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

Le compte PostgreSQL doit avoir le droit de créer une base de test pour
exécuter `python3 manage.py test`.

## Variables d'environnement

| Variable | Rôle | Valeur de développement |
| --- | --- | --- |
| `SECRET_KEY` | Clé cryptographique Django | valeur locale longue et aléatoire |
| `DEBUG` | Active le mode debug | `True` |
| `ALLOWED_HOSTS` | Hôtes autorisés, séparés par des virgules | `localhost,127.0.0.1,[::1]` |
| `POSTGRES_DB` | Nom de la base PostgreSQL | `movie_review` |
| `POSTGRES_USER` | Utilisateur PostgreSQL | `movie_review` |
| `POSTGRES_PASSWORD` | Mot de passe PostgreSQL | valeur locale |
| `POSTGRES_HOST` | Hôte PostgreSQL | `localhost` |
| `POSTGRES_PORT` | Port PostgreSQL | `5432` |

Les options suivantes sont destinées à un vrai environnement HTTPS et restent
désactivées par défaut en développement :

```dotenv
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
```

En production, définir `DEBUG=False`, renseigner les domaines réels dans
`ALLOWED_HOSTS`, utiliser une nouvelle `SECRET_KEY`, puis activer les options
HTTPS adaptées. HSTS ne doit être activé qu'après validation complète du
domaine et de ses sous-domaines.

## Initialisation et lancement

Appliquer les migrations :

```bash
python3 manage.py migrate
```

Créer un superutilisateur :

```bash
python3 manage.py createsuperuser
```

Lancer le serveur de développement :

```bash
python3 manage.py runserver
```

Pages utiles :

- Site : <http://127.0.0.1:8000/>
- Django Admin : <http://127.0.0.1:8000/admin/>
- Dashboard personnalisé : <http://127.0.0.1:8000/dashboard/>

Le dashboard personnalisé est réservé aux utilisateurs staff ou superusers.
Un utilisateur connecté sans ces droits reçoit une réponse HTTP 403.

## Données de démonstration

La commande suivante crée des genres, acteurs, films, castings, critiques,
commentaires et affiches fictives :

```bash
python3 manage.py seed_demo
```

Elle remplace par défaut les anciennes données de démonstration. Pour les
conserver :

```bash
python3 manage.py seed_demo --keep-existing-demo
```

Comptes créés par la commande :

| Rôle | Identifiant | Mot de passe |
| --- | --- | --- |
| Administrateur de démonstration | `demo_admin` | `DemoPass123!` |
| Utilisateur de démonstration | `demo_user_01` | `DemoPass123!` |

Ces comptes et ce mot de passe sont strictement destinés à la démonstration
locale et ne doivent pas être utilisés en production.

## Vérifications et tests

```bash
python3 manage.py check
python3 manage.py makemigrations --check --dry-run
python3 manage.py test
python3 manage.py check --deploy
```

`check --deploy` doit être exécuté avec les variables du véritable
environnement de production. En développement HTTP local, il est normal qu'il
signale les options HTTPS désactivées et une éventuelle clé de développement.

## Structure du projet

```text
MOVIES_REVIEW/
├── accounts/             # Authentification, profil et formulaires utilisateur
├── config/               # Réglages globaux et routage principal
├── dashboard/            # Dashboard personnalisé réservé au staff
├── movies/               # Films, critiques, commentaires et commandes de démo
├── static/               # Styles et scripts globaux
├── templates/            # Base, navigation et pied de page partagés
├── manage.py
├── requirements.txt
└── .env.example
```

## Auteurs

- DIALLOMOHAMED2004
- Kaba516
- Mohamed Sanoussy Sow
- kabamousto

## Limites connues

- Aucun système de signalement, likes, favoris ou notifications.
- Aucun moteur de recherche textuelle avancée.
- Aucun envoi d'email externe configuré par défaut : les emails sont affichés
  dans la console de développement.
- Les listes ne sont pas paginées.
- Le projet utilise le modèle utilisateur Django standard.

## Améliorations futures

- Ajouter une pagination adaptée aux catalogues et listes de modération.
- Configurer un service d'envoi d'emails pour la production.
- Ajouter un système de signalement modéré sans complexifier les commentaires.
- Ajouter une recherche simple sur les films et acteurs.
- Mettre en place une chaîne de déploiement et des tests continus.
