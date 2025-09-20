from django.db import models
from django.conf import settings
from users.models import Department

# Słownik kompetencji dodawany przez HR
class Competency(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
    

# Pytania przypisane do kompetencji
class Question(models.Model):
    SCALE = "scale"
    TEXT = "text"
    BOTH = "both"
    QUESTION_TYPES = [
        (SCALE, "Skala"),
        (TEXT, "Opisowe"),
        (BOTH, "Skala i opis"),
    ]

    text = models.CharField(max_length=255)
    competency = models.ForeignKey(
        "Competency", on_delete=models.SET_NULL, blank=True, null=True, related_name="questions"
    )
    type = models.CharField(max_length=10, choices=QUESTION_TYPES, default=SCALE)
    departments = models.ManyToManyField(
        Department, blank=True, help_text="Wybierz jeden lub więcej działów. Pozostaw puste dla wszystkich."
    )

    def __str__(self):
        return f"{self.text} ({self.get_type_display()})"


# Definicja ankiety - np. ocena roczna dział sprzedaży 2025
class Survey(models.Model):
    name = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    questions = models.ManyToManyField(
        Question,
        through='SurveyQuestion',
        related_name='surveys'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.department.name})"

class SurveyQuestion(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = ('survey', 'question')