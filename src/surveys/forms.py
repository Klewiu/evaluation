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
class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'competency', 'type', 'departments', 'role']
        labels = {
            'text': 'Treść pytania',
            'competency': 'Kompetencja',
            'type': 'Typ pytania',
            'departments': 'Działy',
            'role': 'Dla kogo pytanie',
        }
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Treść pytania'}),
            'competency': forms.Select(attrs={'class': 'form-select', 'id': 'id_competency'}),
            'type': forms.Select(attrs={'class': 'form-select', 'id': 'id_type'}),
            'departments': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'role': forms.Select(attrs={'class': 'form-select'}),
        }

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
                    choices=[(i, str(i)) for i in range(1, 11)],
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
                        MinLengthValidator(10, message="Odpowiedź musi mieć co najmniej 10 znaków."),
                        MaxLengthValidator(500, message="Odpowiedź nie może przekraczać 500 znaków.")
                    ]
                )
            elif q.type == Question.BOTH:
                self.fields[field_name_scale] = forms.ChoiceField(
                    choices=[(i, str(i)) for i in range(1, 11)],
                    widget=forms.RadioSelect(attrs={"class": "form-check-input me-1"}),
                    label=q.text + " (skala)",
                    required=True
                )
                self.fields[field_name_text] = forms.CharField(
                    widget=forms.Textarea(attrs={
                        "class": "form-control form-control-sm mt-2",
                        "rows": 2,
                        "placeholder": "Odpowiedź opisowa..."
                    }),
                    label=q.text + " (uzasadnij powyższą ocenę)",
                    required=True,
                    validators=[
                        MinLengthValidator(20, message="Odpowiedź musi mieć co najmniej 20 znaków."),
                        MaxLengthValidator(2000, message="Odpowiedź nie może przekraczać 2000 znaków.")
                    ]
                )