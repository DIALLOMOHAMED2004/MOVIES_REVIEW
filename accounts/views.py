from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from .forms import (
    EmailOrUsernameAuthenticationForm,
    ProfileUpdateForm,
    RegisterForm,
    StyledPasswordResetForm,
    StyledSetPasswordForm,
)


class RegisterView(FormView):
    """Crée un compte puis renvoie l'utilisateur vers la connexion."""

    # Template utilisé pour afficher le formulaire d'inscription.
    template_name = "accounts/register.html"

    # Formulaire utilisé par cette vue.
    # RegisterForm contient la logique de validation du username,
    # de l'email, du mot de passe et de la confirmation.
    form_class = RegisterForm

    # URL de redirection après une inscription réussie.
    # reverse_lazy est utilisé ici car les URLs ne sont résolues
    # qu'au moment où Django en a besoin.
    success_url = reverse_lazy("accounts:connexion")

    def dispatch(self, request, *args, **kwargs):
        # dispatch est appelé avant get(), post() ou toute autre méthode HTTP.
        # Il permet ici d'empêcher un utilisateur déjà connecté
        # d'accéder à la page d'inscription.
        if request.user.is_authenticated:
            return redirect("accounts:profil")

        # Si l'utilisateur n'est pas connecté,
        # Django continue le traitement normal de la requête.
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Cette méthode est appelée automatiquement lorsque le formulaire
        # d'inscription est valide.

        # Enregistre le nouvel utilisateur en base de données.
        form.save()

        # Ajoute un message de succès qui sera affiché sur la page suivante.
        messages.success(
            self.request,
            "Votre compte a été créé avec succès. Vous pouvez maintenant vous connecter.",
        )

        # Continue le comportement standard de FormView :
        # redirection vers success_url.
        return super().form_valid(form)


class UserLoginView(LoginView):
    """Connexion par nom d'utilisateur ou par adresse email."""

    # Template utilisé pour afficher la page de connexion.
    template_name = "accounts/login.html"

    # Formulaire d'authentification personnalisé.
    # Il accepte soit le username, soit l'adresse email.
    authentication_form = EmailOrUsernameAuthenticationForm

    # Si un utilisateur déjà connecté essaie d'ouvrir la page de connexion,
    # Django le redirige automatiquement au lieu d'afficher le formulaire.
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    """Déconnexion conforme à Django 6 : requête POST obligatoire."""

    # Page vers laquelle l'utilisateur est redirigé après déconnexion.
    next_page = reverse_lazy("movies:accueil")


class UserPasswordResetView(PasswordResetView):
    """Démarre le flux sécurisé de réinitialisation par email de Django."""

    # Template affichant le formulaire où l'utilisateur saisit son email.
    template_name = "accounts/password_reset_form.html"

    # Formulaire personnalisé utilisé pour styliser le champ email.
    form_class = StyledPasswordResetForm

    # Template texte utilisé pour générer le contenu de l'email envoyé.
    email_template_name = "accounts/password_reset_email.txt"

    # Template utilisé pour générer le sujet de l'email.
    subject_template_name = "accounts/password_reset_subject.txt"

    # URL vers laquelle Django redirige après une demande envoyée.
    success_url = reverse_lazy("accounts:password_reset_done")


class UserPasswordResetDoneView(PasswordResetDoneView):
    """Indique qu'un email de réinitialisation a été envoyé si possible."""

    # Template affiché après la soumission du formulaire de réinitialisation.
    template_name = "accounts/password_reset_done.html"


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    """Valide le token reçu par email et définit un nouveau mot de passe."""

    # Template contenant le formulaire de saisie du nouveau mot de passe.
    template_name = "accounts/password_reset_confirm.html"

    # Formulaire personnalisé utilisé pour styliser les champs du nouveau mot de passe.
    form_class = StyledSetPasswordForm

    # Empêche Django de connecter automatiquement l'utilisateur
    # après la réinitialisation du mot de passe.
    post_reset_login = False

    # URL de redirection après changement réussi du mot de passe.
    success_url = reverse_lazy("accounts:password_reset_complete")


class UserPasswordResetCompleteView(PasswordResetCompleteView):
    """Termine le flux sans connecter automatiquement l'utilisateur."""

    # Template affiché une fois le mot de passe réinitialisé avec succès.
    template_name = "accounts/password_reset_complete.html"


class ProfileView(LoginRequiredMixin, TemplateView):
    """Affiche les informations du compte de l'utilisateur connecté."""

    # Template utilisé pour afficher le profil utilisateur.
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        # Récupère d'abord le contexte standard fourni par TemplateView.
        context = super().get_context_data(**kwargs)

        # Utilisateur actuellement connecté.
        user = self.request.user

        # Récupère toutes les critiques publiées par cet utilisateur.
        # select_related("film__genre") optimise les requêtes SQL :
        # Django récupère le film et son genre dans la même requête.
        # order_by("-date_publication") affiche les critiques les plus récentes d'abord.
        reviews = list(
            user.critiques.select_related("film__genre").order_by("-date_publication")
        )

        # Ajoute la liste des critiques au contexte du template.
        context["reviews"] = reviews

        # Ajoute le nombre total de critiques au contexte.
        context["review_count"] = len(reviews)

        # Ajoute le nombre total de commentaires publiés par l'utilisateur.
        context["comment_count"] = user.commentaires.count()

        # Retourne le contexte enrichi au template.
        return context


class ProfileEditView(LoginRequiredMixin, TemplateView):
    """Modifie le profil et, si demandé, le mot de passe sur le même écran."""

    # Template affichant le formulaire de modification du profil.
    template_name = "accounts/profile_edit.html"

    # Liste des champs liés au changement de mot de passe.
    # Elle permet de détecter si l'utilisateur souhaite réellement
    # changer son mot de passe ou seulement modifier son profil.
    password_fields = ("old_password", "new_password1", "new_password2")

    def get_context_data(self, **kwargs):
        # Récupère le contexte standard fourni par TemplateView.
        context = super().get_context_data(**kwargs)

        # Ajoute le formulaire de profil au contexte si aucune autre valeur
        # n'a déjà été fournie.
        # Cela permet notamment de réutiliser cette méthode après une erreur
        # sans écraser un formulaire déjà rempli.
        context.setdefault(
            "profile_form",
            ProfileUpdateForm(instance=self.request.user),
        )

        # Ajoute le formulaire de changement de mot de passe au contexte,
        # uniquement s'il n'existe pas déjà.
        context.setdefault(
            "password_form",
            self._build_password_form(),
        )

        # Retourne le contexte utilisé par le template.
        return context

    def post(self, request, *args, **kwargs):
        # Cette méthode gère l'envoi du formulaire de modification du profil.

        # Formulaire de mise à jour du username et de l'email.
        # request.POST contient les données envoyées par l'utilisateur.
        # instance=request.user indique que l'on modifie l'utilisateur connecté.
        profile_form = ProfileUpdateForm(request.POST, instance=request.user)

        # Détermine si l'utilisateur a rempli au moins un champ de mot de passe.
        password_requested = self._password_change_requested(request.POST)

        # Si un changement de mot de passe est demandé,
        # on transmet request.POST au formulaire PasswordChangeForm.
        # Sinon, on lui transmet None pour éviter de déclencher sa validation.
        password_data = request.POST if password_requested else None

        # Construit le formulaire de changement de mot de passe,
        # soit vide, soit rempli avec les données POST.
        password_form = self._build_password_form(password_data)

        # Le profil doit toujours être valide.
        # Le formulaire de mot de passe n'est exigé que si l'utilisateur
        # a effectivement demandé un changement de mot de passe.
        if profile_form.is_valid() and (
            not password_requested or password_form.is_valid()
        ):
            # Enregistre les changements du profil.
            profile_form.save()

            if password_requested:
                # Enregistre le nouveau mot de passe.
                user = password_form.save()

                # Met à jour la session de l'utilisateur après changement
                # de mot de passe.
                # Sans cela, Django pourrait invalider la session actuelle.
                update_session_auth_hash(request, user)

                # Message affiché après modification du profil et du mot de passe.
                messages.success(
                    request,
                    "Votre profil et votre mot de passe ont été mis à jour.",
                )
            else:
                # Message affiché lorsque seul le profil a été modifié.
                messages.success(
                    request,
                    "Vos modifications ont été enregistrées avec succès.",
                )

            # Redirige vers la page de profil après succès.
            return redirect("accounts:profil")

        # Si au moins un formulaire est invalide,
        # on réaffiche la page avec les erreurs.
        return render(
            request,
            self.template_name,
            {
                "profile_form": profile_form,
                "password_form": password_form,
            },
        )

    def _build_password_form(self, data=None):
        # Méthode utilitaire interne.
        # Elle construit un PasswordChangeForm associé à l'utilisateur connecté.
        # Si data vaut None, le formulaire est non soumis.
        # Si data contient request.POST, le formulaire est soumis et validable.
        form = PasswordChangeForm(self.request.user, data)

        # Personnalisation des libellés des champs.
        form.fields["old_password"].label = "Mot de passe actuel"
        form.fields["new_password1"].label = "Nouveau mot de passe"
        form.fields["new_password1"].help_text = "Au moins 8 caractères recommandés."
        form.fields["new_password2"].label = "Confirmer le nouveau mot de passe"

        # Placeholders affichés dans les champs du formulaire.
        placeholders = {
            "old_password": "Votre mot de passe actuel",
            "new_password1": "Votre nouveau mot de passe",
            "new_password2": "Confirmez votre nouveau mot de passe",
        }

        # Attributs autocomplete adaptés à chaque champ de mot de passe.
        autocomplete = {
            "old_password": "current-password",
            "new_password1": "new-password",
            "new_password2": "new-password",
        }

        # Applique à chaque champ les classes CSS et attributs HTML nécessaires.
        for name, field in form.fields.items():
            field.widget.attrs.update(
                {
                    "class": "form-control",
                    "autocomplete": autocomplete.get(name, ""),
                    "placeholder": placeholders.get(name, ""),
                }
            )

        # Retourne le formulaire prêt à être affiché ou validé.
        return form

    def _password_change_requested(self, data):
        # Détermine si l'utilisateur a commencé à remplir les champs
        # de changement de mot de passe.
        # any(...) retourne True si au moins un des champs contient une valeur.
        return any(data.get(field) for field in self.password_fields)