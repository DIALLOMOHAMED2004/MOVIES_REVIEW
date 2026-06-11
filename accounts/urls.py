from django.urls import path

from .views import (
    ProfileEditView,
    ProfileView,
    RegisterView,
    UserLoginView,
    UserLogoutView,
    UserPasswordResetCompleteView,
    UserPasswordResetConfirmView,
    UserPasswordResetDoneView,
    UserPasswordResetView,
)

app_name = "accounts"

urlpatterns = [
    path("connexion/", UserLoginView.as_view(), name="connexion"),
    path("inscription/", RegisterView.as_view(), name="inscription"),
    path("deconnexion/", UserLogoutView.as_view(), name="deconnexion"),
    path("password-reset/", UserPasswordResetView.as_view(), name="password_reset"),
    path(
        "password-reset/envoye/",
        UserPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        UserPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/termine/",
        UserPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("profil/", ProfileView.as_view(), name="profil"),
    path("profil/modifier/", ProfileEditView.as_view(), name="modifier_profil"),
]