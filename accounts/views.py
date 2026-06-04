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

    template_name = "accounts/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy("accounts:connexion")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("accounts:profil")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request,
            "Votre compte a été créé avec succès. Vous pouvez maintenant vous connecter.",
        )
        return super().form_valid(form)


class UserLoginView(LoginView):
    """Connexion par nom d'utilisateur ou par adresse email."""

    template_name = "accounts/login.html"
    authentication_form = EmailOrUsernameAuthenticationForm
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    """Déconnexion conforme à Django 6 : requête POST obligatoire."""

    next_page = reverse_lazy("movies:accueil")


class UserPasswordResetView(PasswordResetView):
    """Démarre le flux sécurisé de réinitialisation par email de Django."""

    template_name = "accounts/password_reset_form.html"
    form_class = StyledPasswordResetForm
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class UserPasswordResetDoneView(PasswordResetDoneView):
    """Indique qu'un email de réinitialisation a été envoyé si possible."""

    template_name = "accounts/password_reset_done.html"


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    """Valide le token reçu par email et définit un nouveau mot de passe."""

    template_name = "accounts/password_reset_confirm.html"
    form_class = StyledSetPasswordForm
    post_reset_login = False
    success_url = reverse_lazy("accounts:password_reset_complete")


class UserPasswordResetCompleteView(PasswordResetCompleteView):
    """Termine le flux sans connecter automatiquement l'utilisateur."""

    template_name = "accounts/password_reset_complete.html"


class ProfileView(LoginRequiredMixin, TemplateView):
    """Affiche les informations du compte de l'utilisateur connecté."""

    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        reviews = list(
            user.critiques.select_related("film__genre").order_by("-date_publication")
        )
        context["reviews"] = reviews
        context["review_count"] = len(reviews)
        context["comment_count"] = user.commentaires.count()
        return context


class ProfileEditView(LoginRequiredMixin, TemplateView):
    """Modifie le profil et, si demandé, le mot de passe sur le même écran."""

    template_name = "accounts/profile_edit.html"
    password_fields = ("old_password", "new_password1", "new_password2")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault(
            "profile_form",
            ProfileUpdateForm(instance=self.request.user),
        )
        context.setdefault(
            "password_form",
            self._build_password_form(),
        )
        return context

    def post(self, request, *args, **kwargs):
        profile_form = ProfileUpdateForm(request.POST, instance=request.user)
        password_requested = self._password_change_requested(request.POST)
        password_data = request.POST if password_requested else None
        password_form = self._build_password_form(password_data)

        if profile_form.is_valid() and (
            not password_requested or password_form.is_valid()
        ):
            profile_form.save()

            if password_requested:
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(
                    request,
                    "Votre profil et votre mot de passe ont été mis à jour.",
                )
            else:
                messages.success(
                    request,
                    "Vos modifications ont été enregistrées avec succès.",
                )

            return redirect("accounts:profil")

        return render(
            request,
            self.template_name,
            {
                "profile_form": profile_form,
                "password_form": password_form,
            },
        )

    def _build_password_form(self, data=None):
        form = PasswordChangeForm(self.request.user, data)
        form.fields["old_password"].label = "Mot de passe actuel"
        form.fields["new_password1"].label = "Nouveau mot de passe"
        form.fields["new_password1"].help_text = "Au moins 8 caractères recommandés."
        form.fields["new_password2"].label = "Confirmer le nouveau mot de passe"

        placeholders = {
            "old_password": "Votre mot de passe actuel",
            "new_password1": "Votre nouveau mot de passe",
            "new_password2": "Confirmez votre nouveau mot de passe",
        }
        autocomplete = {
            "old_password": "current-password",
            "new_password1": "new-password",
            "new_password2": "new-password",
        }
        for name, field in form.fields.items():
            field.widget.attrs.update(
                {
                    "class": "form-control",
                    "autocomplete": autocomplete.get(name, ""),
                    "placeholder": placeholders.get(name, ""),
                }
            )
        return form

    def _password_change_requested(self, data):
        return any(data.get(field) for field in self.password_fields)
