from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import resolve_url


class StaffRequiredMixin:
    """Restreint une vue aux utilisateurs staff ou superusers."""

    # Ce mixin est destiné à être utilisé avec des vues basées sur des classes.
    #
    # Exemple d'utilisation :
    #
    # class DashboardView(StaffRequiredMixin, TemplateView):
    #     ...
    #
    # Il permet de centraliser la logique de protection du dashboard personnalisé :
    # - un utilisateur non connecté est redirigé vers la page de connexion ;
    # - un utilisateur connecté mais non staff reçoit une erreur 403 ;
    # - un utilisateur staff ou superuser peut accéder à la vue.
    #
    # L'ordre d'héritage est important :
    # StaffRequiredMixin doit généralement être placé avant la vue générique Django
    # pour que sa méthode dispatch soit appelée en premier.

    def dispatch(self, request, *args, **kwargs):
        # dispatch est la méthode centrale appelée par Django avant get(), post(),
        # put(), delete(), etc.
        #
        # En plaçant la vérification d'accès ici, on protège automatiquement
        # toutes les méthodes HTTP de la vue concernée.
        #
        # Cela évite par exemple qu'une route soit protégée en GET mais oubliée en POST.

        # Premier cas : l'utilisateur n'est pas connecté.
        if not request.user.is_authenticated:

            # Redirige l'utilisateur anonyme vers la page de connexion.
            #
            # request.get_full_path() conserve l'URL exacte demandée,
            # y compris les éventuels paramètres de requête.
            #
            # Django l'utilise ensuite comme valeur du paramètre "next",
            # afin que l'utilisateur puisse revenir à la page demandée
            # après une connexion réussie.
            return redirect_to_login(
                request.get_full_path(),

                # resolve_url(settings.LOGIN_URL) transforme la valeur LOGIN_URL
                # en URL concrète.
                #
                # settings.LOGIN_URL peut être :
                # - une URL directe ;
                # - un nom de route Django ;
                # - une valeur résoluble par reverse().
                resolve_url(settings.LOGIN_URL),
            )

        # Deuxième cas : l'utilisateur est connecté,
        # mais il n'a pas les droits nécessaires pour accéder au dashboard.
        #
        # is_staff correspond aux utilisateurs autorisés à accéder
        # à l'administration ou aux espaces internes.
        #
        # is_superuser correspond aux utilisateurs ayant tous les droits.
        if not (request.user.is_staff or request.user.is_superuser):

            # PermissionDenied déclenche une réponse HTTP 403.
            #
            # Ici, on ne redirige pas vers la connexion,
            # car l'utilisateur est déjà authentifié.
            # Le problème n'est donc pas l'absence de connexion,
            # mais l'absence d'autorisation.
            raise PermissionDenied

        # Troisième cas : l'utilisateur est connecté et possède les droits requis.
        #
        # On délègue alors la suite du traitement à la vue parente.
        # Selon la méthode HTTP, Django appellera ensuite get(), post(), etc.
        return super().dispatch(request, *args, **kwargs)