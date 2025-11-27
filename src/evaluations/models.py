from django.db import models
from django.conf import settings
from surveys.models import SurveyResponse, Question

class EmployeeEvaluation(models.Model):

    STATUS_CHOICES = [
        ("draft", "W trakcie oceny"),
        ("submitted", "Zakończona"),
    ]


    employee_response = models.ForeignKey(
        SurveyResponse,
        on_delete=models.CASCADE,
        related_name="evaluations",
        help_text="Ankieta wypełniona przez pracownika"
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        help_text="Pytanie z ankiety pracownika"
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        help_text="Manager oceniający pracownika"
    )
    scale_value = models.IntegerField(null=True, blank=True)
    text_value = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
        help_text="Status oceny managera"
    )


    class Meta:
        unique_together = ('employee_response', 'question', 'manager')

    def __str__(self):
        return f"{self.manager} ocenia {self.employee_response.user} → {self.question.text}"
