from django import forms

from movies.models import Acteur, Casting, Film, Genre


class DashboardModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-control")


class FilmForm(DashboardModelForm):
    acteurs = forms.ModelMultipleChoiceField(
        queryset=Acteur.objects.all(),
        required=False,
        label="Acteurs",
        widget=forms.SelectMultiple(attrs={"class": "form-control"}),
        help_text="Sélectionnez les acteurs déjà créés à associer au film.",
    )

    class Meta:
        model = Film
        fields = (
            "titre",
            "synopsis",
            "genre",
            "date_sortie",
            "duree_minutes",
            "affiche",
            "acteurs",
        )
        widgets = {
            "date_sortie": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
            "synopsis": forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["acteurs"].queryset = Acteur.objects.all()
        if self.instance.pk:
            self.fields["acteurs"].initial = self.instance.acteurs.all()

    def sync_casting(self, film):
        selected_ids = set(self.cleaned_data["acteurs"].values_list("id", flat=True))
        existing_ids = set(film.castings.values_list("acteur_id", flat=True))

        film.castings.exclude(acteur_id__in=selected_ids).delete()
        Casting.objects.bulk_create(
            [
                Casting(film=film, acteur_id=acteur_id)
                for acteur_id in selected_ids - existing_ids
            ]
        )


class GenreForm(DashboardModelForm):
    class Meta:
        model = Genre
        fields = ("nom",)


class ActeurForm(DashboardModelForm):
    class Meta:
        model = Acteur
        fields = ("nom",)
