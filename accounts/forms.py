from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
    UsernameField,
)
from django.core.exceptions import ValidationError


# Récupère dynamiquement le modèle utilisateur actif du projet.
# Cela permet de rester compatible avec le modèle User par défaut de Django
# ou avec un éventuel modèle utilisateur personnalisé défini dans settings.AUTH_USER_MODEL.
User = get_user_model()


class RegisterForm(UserCreationForm):
    """Formulaire d'inscription basé sur l'utilisateur Django standard."""

    # Champ email ajouté explicitement au formulaire d'inscription.
    # UserCreationForm ne gère normalement que username, password1 et password2.
    # Ici, l'email devient obligatoire afin que chaque compte possède une adresse email.
    email = forms.EmailField(
        label="Adresse email",
        required=True,
        help_text="Nous ne partagerons jamais votre email.",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "autocomplete": "email",
                "placeholder": "exemple@email.com",
            }
        ),
    )

    class Meta(UserCreationForm.Meta):
        # Définit le modèle utilisé par le formulaire.
        # Ici, on utilise le modèle utilisateur actif récupéré plus haut.
        model = User

        # Liste des champs affichés dans le formulaire d'inscription.
        # password1 et password2 viennent directement de UserCreationForm.
        fields = ("username", "email", "password1", "password2")

        # Personnalisation HTML du champ username.
        # La classe form-control permet d'appliquer le style CSS global du projet.
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "username",
                    "placeholder": "Votre nom d'utilisateur",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        # Appelle le constructeur parent afin que Django initialise correctement
        # tous les champs standards de UserCreationForm.
        super().__init__(*args, **kwargs)

        # Personnalisation du libellé affiché pour le champ username.
        self.fields["username"].label = "Nom d'utilisateur"

        # Texte d'aide affiché sous le champ username.
        # Il informe l'utilisateur que ce nom sera visible publiquement.
        self.fields["username"].help_text = (
            "Votre nom d'utilisateur sera visible publiquement."
        )

        # Personnalisation du champ password1.
        self.fields["password1"].label = "Mot de passe"
        self.fields["password1"].help_text = "Au moins 8 caractères recommandés."

        # Ajout d'attributs HTML au champ password1.
        # autocomplete="new-password" indique au navigateur qu'il s'agit
        # d'un nouveau mot de passe à créer.
        self.fields["password1"].widget.attrs.update(
            {
                "class": "form-control",
                "autocomplete": "new-password",
                "placeholder": "Votre mot de passe",
            }
        )

        # Personnalisation du champ de confirmation du mot de passe.
        self.fields["password2"].label = "Confirmer le mot de passe"

        # Ajout d'attributs HTML au champ password2.
        self.fields["password2"].widget.attrs.update(
            {
                "class": "form-control",
                "autocomplete": "new-password",
                "placeholder": "Confirmez votre mot de passe",
            }
        )

    def clean_email(self):
        # Récupère l'email saisi par l'utilisateur.
        # strip() supprime les espaces inutiles au début et à la fin.
        # lower() normalise l'email en minuscules pour éviter les doublons
        # du type Test@Email.com et test@email.com.
        email = self.cleaned_data["email"].strip().lower()

        # Vérifie si un utilisateur possède déjà cette adresse email.
        # email__iexact effectue une comparaison insensible à la casse.
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Cette adresse email est déjà utilisée.")

        # Retourne l'email nettoyé qui sera ensuite utilisé par le formulaire.
        return email


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    """Authentifie un utilisateur avec son nom d'utilisateur ou son email."""

    # Redéfinit le champ username du formulaire d'authentification Django.
    # Même si le champ s'appelle techniquement username,
    # il accepte ici soit un nom d'utilisateur, soit une adresse email.
    username = UsernameField(
        label="Nom d'utilisateur ou email",
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "class": "form-control",
                "autocomplete": "username",
                "placeholder": "Nom d'utilisateur ou email",
            }
        ),
    )

    # Messages d'erreur personnalisés affichés en cas d'échec de connexion.
    error_messages = {
        "invalid_login": (
            "Identifiants incorrects. Veuillez vérifier votre nom d'utilisateur, "
            "votre email et votre mot de passe."
        ),
        "inactive": "Ce compte est inactif.",
    }

    def clean(self):
        # Récupère l'identifiant saisi dans le champ username.
        # Cet identifiant peut être un nom d'utilisateur ou un email.
        identifier = self.cleaned_data.get("username")

        # Récupère le mot de passe saisi.
        password = self.cleaned_data.get("password")

        # La tentative d'authentification ne se fait que si les deux champs
        # nécessaires sont présents.
        if identifier is not None and password:
            # Par défaut, on considère que l'identifiant saisi est un username.
            auth_username = identifier

            # Si l'identifiant contient "@", on suppose qu'il s'agit d'un email.
            if "@" in identifier:
                try:
                    # Recherche l'utilisateur correspondant à cet email,
                    # sans tenir compte de la casse.
                    user = User.objects.get(email__iexact=identifier)

                except User.DoesNotExist:
                    # Si aucun utilisateur n'existe avec cet email,
                    # on laisse auth_username tel quel.
                    # L'authentification échouera ensuite normalement.
                    pass

                except User.MultipleObjectsReturned:
                    # Cas de sécurité : plusieurs utilisateurs ont le même email.
                    # Cela ne devrait normalement pas arriver si l'unicité est bien contrôlée.
                    # On refuse donc la connexion avec une erreur générique.
                    raise self.get_invalid_login_error()

                else:
                    # Si un utilisateur est trouvé par email,
                    # on récupère son vrai username pour utiliser le système
                    # d'authentification standard de Django.
                    auth_username = user.get_username()

            # Authentifie l'utilisateur via le backend Django.
            # Django attend généralement username + password.
            self.user_cache = authenticate(
                self.request,
                username=auth_username,
                password=password,
            )

            # Si authenticate retourne None, les identifiants sont invalides.
            if self.user_cache is None:
                raise self.get_invalid_login_error()

            # Vérifie si l'utilisateur est autorisé à se connecter.
            # Par exemple, cette méthode bloque les comptes inactifs.
            self.confirm_login_allowed(self.user_cache)

        # Retourne les données nettoyées du formulaire.
        return self.cleaned_data

    def __init__(self, request=None, *args, **kwargs):
        # Initialise le formulaire parent AuthenticationForm.
        super().__init__(request, *args, **kwargs)

        # Personnalise le libellé du champ mot de passe.
        self.fields["password"].label = "Mot de passe"

        # Ajoute les classes CSS et attributs HTML nécessaires au champ password.
        self.fields["password"].widget.attrs.update(
            {
                "class": "form-control",
                "autocomplete": "current-password",
                "placeholder": "Votre mot de passe",
            }
        )


class StyledPasswordResetForm(PasswordResetForm):
    """Formulaire natif Django stylé pour la demande de réinitialisation."""

    # Champ email utilisé pour demander la réinitialisation du mot de passe.
    # PasswordResetForm contient déjà la logique Django nécessaire pour envoyer
    # un email de réinitialisation si l'adresse correspond à un compte existant.
    email = forms.EmailField(
        label="Adresse email",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "autocomplete": "email",
                "placeholder": "Votre adresse email",
            }
        ),
    )


class StyledSetPasswordForm(SetPasswordForm):
    """Formulaire natif Django stylé pour définir un nouveau mot de passe."""

    def __init__(self, user, *args, **kwargs):
        # Initialise le formulaire parent SetPasswordForm.
        # Le paramètre user est obligatoire car Django doit savoir
        # pour quel utilisateur le mot de passe sera modifié.
        super().__init__(user, *args, **kwargs)

        # Personnalisation du premier champ de nouveau mot de passe.
        self.fields["new_password1"].label = "Nouveau mot de passe"
        self.fields["new_password1"].help_text = "Au moins 8 caractères recommandés."

        # Ajout des classes CSS et attributs HTML du champ new_password1.
        self.fields["new_password1"].widget.attrs.update(
            {
                "class": "form-control",
                "autocomplete": "new-password",
                "placeholder": "Votre nouveau mot de passe",
            }
        )

        # Personnalisation du champ de confirmation du nouveau mot de passe.
        self.fields["new_password2"].label = "Confirmer le nouveau mot de passe"

        # Ajout des classes CSS et attributs HTML du champ new_password2.
        self.fields["new_password2"].widget.attrs.update(
            {
                "class": "form-control",
                "autocomplete": "new-password",
                "placeholder": "Confirmez votre nouveau mot de passe",
            }
        )


class ProfileUpdateForm(forms.ModelForm):
    """Formulaire de modification des informations personnelles du compte."""

    class Meta:
        # Le formulaire est lié au modèle utilisateur actif du projet.
        model = User

        # Champs autorisés à être modifiés depuis le profil.
        # On limite volontairement la modification à username et email.
        fields = ("username", "email")

        # Libellés affichés dans le formulaire HTML.
        labels = {
            "username": "Nom d'utilisateur",
            "email": "Adresse email",
        }

        # Textes d'aide affichés sous certains champs.
        help_texts = {
            "username": "Votre nom d'utilisateur sera visible publiquement.",
        }

        # Personnalisation des widgets HTML utilisés pour les champs.
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control", "autocomplete": "username"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "autocomplete": "email"}
            ),
        }

    def __init__(self, *args, **kwargs):
        # Initialise le formulaire parent ModelForm.
        super().__init__(*args, **kwargs)

        # Rend explicitement le champ email obligatoire.
        # Même si le modèle User standard de Django n'impose pas toujours l'email,
        # ce projet considère qu'un compte doit obligatoirement en avoir un.
        self.fields["email"].required = True

    def clean_username(self):
        # Récupère le nom d'utilisateur saisi et retire les espaces inutiles.
        username = self.cleaned_data["username"].strip()

        # Recherche les utilisateurs ayant déjà ce username,
        # sans tenir compte de la casse.
        queryset = User.objects.filter(username__iexact=username)

        # Si le formulaire modifie un utilisateur déjà existant,
        # on exclut cet utilisateur de la recherche.
        # Cela permet à un utilisateur de conserver son propre username
        # sans déclencher une erreur de doublon.
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        # Si un autre utilisateur possède déjà ce username,
        # on bloque la validation du formulaire.
        if queryset.exists():
            raise ValidationError("Ce nom d'utilisateur est déjà pris.")

        # Retourne le username nettoyé.
        return username

    def clean_email(self):
        # Récupère l'email saisi, supprime les espaces inutiles,
        # puis le convertit en minuscules pour normaliser la donnée.
        email = self.cleaned_data["email"].strip().lower()

        # Vérifie que l'email n'est pas vide.
        if not email:
            raise ValidationError("L'adresse email est obligatoire.")

        # Recherche les utilisateurs ayant déjà cet email,
        # sans tenir compte de la casse.
        queryset = User.objects.filter(email__iexact=email)

        # Si le formulaire concerne un utilisateur existant,
        # on exclut cet utilisateur de la vérification d'unicité.
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        # Si un autre utilisateur utilise déjà cet email,
        # on refuse la modification.
        if queryset.exists():
            raise ValidationError("Cette adresse email est déjà utilisée.")

        # Retourne l'email nettoyé.
        return email