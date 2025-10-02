from django import forms
from .models import Competency, Question, Survey, SurveyQuestion

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
            'year': 'Rok',
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
