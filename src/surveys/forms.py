from django import forms
from .models import Competency, Question, Survey, SurveyQuestion
from django.core.validators import MinLengthValidator, MaxLengthValidator

# Formularz do dodawania/edycji kompetencji
class CompetencyForm(forms.ModelForm):
    class Meta:
        model = Competency
        fields = ['name', 'description']
        labels = {
            'name': 'Nazwa kompetencji',
            'description': 'Opis kompetencji',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nazwa kompetencji'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Opis kompetencji'}),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        # Wykluczamy obiekt, jeśli edytujemy już istniejący
        qs = Competency.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Taka kompetencja już istnieje!")
        return name
ROLE_ADD_CHOICES = [
    ("manager", "Manager"),
    ("employee", "Pracownik"),
    ("team_leader", "Team Leader"),
    ("account_executive", "Account Executive"),
]


class QuestionAddForm(forms.ModelForm):
    roles = forms.MultipleChoiceField(
        choices=ROLE_ADD_CHOICES,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 4}),
        label='Dla kogo pytanie',
        required=True,
    )

    class Meta:
        model = Question
        fields = ['text', 'competency', 'type', 'departments']
        labels = {
            'text': 'Treść pytania',
            'competency': 'Kompetencja',
            'type': 'Typ pytania',
            'departments': 'Działy',
        }
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Treść pytania'}),
            'competency': forms.Select(attrs={'class': 'form-select', 'id': 'id_competency'}),
            'type': forms.Select(attrs={'class': 'form-select', 'id': 'id_type'}),
            'departments': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
        }

    def clean(self):
        cleaned_data = super().clean()
        competency = cleaned_data.get('competency')
        type_value = cleaned_data.get('type')

        if competency and type_value == Question.TEXT:
            self.add_error('type', 'Nie możesz wybrać typu "Opisowe" dla pytań z ustawioną kompetencją.')


class QuestionForm(forms.ModelForm):
    roles = forms.MultipleChoiceField(
        choices=ROLE_ADD_CHOICES,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 4}),
        label='Dla kogo pytanie',
        required=True,
    )

    class Meta:
        model = Question
        fields = ['text', 'competency', 'type', 'departments']
        labels = {
            'text': 'Treść pytania',
            'competency': 'Kompetencja',
            'type': 'Typ pytania',
            'departments': 'Działy',
        }
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Treść pytania'}),
            'competency': forms.Select(attrs={'class': 'form-select', 'id': 'id_competency'}),
            'type': forms.Select(attrs={'class': 'form-select', 'id': 'id_type'}),
            'departments': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.role:
            role = self.instance.role
            all_roles = [r[0] for r in ROLE_ADD_CHOICES]
            if role in ('all', 'both'):
                self.fields['roles'].initial = all_roles
            elif role in all_roles:
                self.fields['roles'].initial = [role]

    def clean(self):
        cleaned_data = super().clean()
        competency = cleaned_data.get('competency')
        type_value = cleaned_data.get('type')

        if competency and type_value == Question.TEXT:
            self.add_error('type', 'Nie możesz wybrać typu "Opisowe" dla pytań z ustawioną kompetencją.')


class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = ['name', 'department', 'year', 'role']  # dodaliśmy role
        labels = {
            'name': 'Nazwa ankiety',
            'department': 'Dział',
            'year': 'Oceniany rok',
            'role': 'Rola użytkownika',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nazwa ankiety'}),

            # Dział – zostawiamy HTMX
            'department': forms.Select(attrs={
                'class': 'form-select',
                'hx-get': '/surveys/load-questions/',
                'hx-target': '#questions-container',
                'hx-trigger': 'change'
            }),

            # Rok
            'year': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Wpisz rok np. 2025',
                'min': 2000,
                'max': 2100
            }),

            # Rola – też podpinamy do HTMX
            'role': forms.Select(attrs={
                'class': 'form-select',
                'hx-get': '/surveys/load-questions/',
                'hx-target': '#questions-container',
                'hx-trigger': 'change'
            }),
        }


class SurveyFillForm(forms.Form):
    def __init__(self, survey, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.survey = survey

        for sq in survey.surveyquestion_set.select_related("question").all():
            q = sq.question
            field_name_scale = f"q{q.id}_scale"
            field_name_text = f"q{q.id}_text"

            if q.type == Question.SCALE:
                self.fields[field_name_scale] = forms.ChoiceField(
                    choices=[(i, str(i)) for i in range(0, 5)],
                    widget=forms.RadioSelect(attrs={"class": "form-check-input me-1"}),
                    label=q.text,
                    required=True
                )
            elif q.type == Question.TEXT:
                self.fields[field_name_text] = forms.CharField(
                    widget=forms.Textarea(attrs={
                        "class": "form-control form-control-sm mt-2",
                        "rows": 2,
                        "placeholder": "Odpowiedź opisowa..."
                    }),
                    label=q.text,
                    required=True,
                    validators=[
                        MinLengthValidator(20, message="Odpowiedź musi mieć co najmniej 20 znaków."),
                        MaxLengthValidator(500, message="Odpowiedź nie może przekraczać 500 znaków.")
                    ]
                )
            elif q.type == Question.BOTH:
                self.fields[field_name_scale] = forms.ChoiceField(
                    choices=[(i, str(i)) for i in range(0, 5)],
                    widget=forms.RadioSelect(attrs={"class": "form-check-input me-1"}),
                    label=q.text,
                    required=True
                )
                self.fields[field_name_text] = forms.CharField(
                    widget=forms.Textarea(attrs={
                        "class": "form-control form-control-sm mt-2",
                        "rows": 2,
                        "placeholder": "Odpowiedź opisowa..."
                    }),
                    label="Uzasadnij powyższą ocenę",
                    required=True,
                    validators=[
                        MinLengthValidator(20, message="Odpowiedź musi mieć co najmniej 20 znaków."),
                        MaxLengthValidator(2000, message="Odpowiedź nie może przekraczać 2000 znaków.")
                    ]
                )

    def grouped_fields(self):
        """Yields (counter, q_type, scale_field, text_field) grouped per question."""
        counter = 0
        for sq in self.survey.surveyquestion_set.select_related("question").all():
            q = sq.question
            counter += 1
            scale_field = self[f"q{q.id}_scale"] if q.type in (Question.SCALE, Question.BOTH) else None
            text_field = self[f"q{q.id}_text"] if q.type in (Question.TEXT, Question.BOTH) else None
            yield counter, q.type, scale_field, text_field