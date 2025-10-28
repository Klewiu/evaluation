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
    ROLE_CHOICES = [
        ("both", "Pracownik i Manager"),
        ("manager", "Manager"),
        ("employee", "Pracownik"),
    ]

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
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default="both", help_text="Dla kogo pytanie?"
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.text} ({self.get_type_display()}) → {self.get_role_display()}"

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
    year = models.PositiveIntegerField(blank=True, null=True)

    ROLE_CHOICES = [
        # ("both", "Pracownik i Manager"),
        ("manager", "Manager"),
        ("employee", "Pracownik"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="both")

    def __str__(self):
        return f"{self.name} ({self.department.name}, {self.year or self.created_at.year}, {self.get_role_display()})"


class SurveyQuestion(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = ('survey', 'question')


class SurveyResponse(models.Model):
    STATUS_CHOICES = [
        ("draft", "W trakcie wypełniania"),
        ("submitted", "Wypełniona"),
        ("closed", "Zakończona"),
    ]

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    def __str__(self):
        return f"{self.user} → {self.survey} ({self.get_status_display()})"

class SurveyAnswer(models.Model):
    response = models.ForeignKey(SurveyResponse, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    scale_value = models.IntegerField(null=True, blank=True)
    text_value = models.TextField(blank=True)

    def __str__(self):
        return f"Odpowiedź na {self.question.text}"