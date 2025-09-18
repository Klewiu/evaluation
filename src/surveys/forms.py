from django import forms
from .models import Competency, Question

# Formularz do dodawania/edycji kompetencji
class CompetencyForm(forms.ModelForm):
    class Meta:
        model = Competency
        fields = ['name', 'description', 'departments']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nazwa kompetencji'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Opis kompetencji'}),
            'departments': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
        }
class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'competency', 'type', 'departments']
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
