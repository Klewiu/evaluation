from django.contrib.auth.models import AbstractUser 
from django.db import models
from django.conf import settings


# -------------------------------------------
# DEPARTAMENTY
# -------------------------------------------
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Dział"
        verbose_name_plural = "Działy"


# -------------------------------------------
# UŻYTKOWNIK
# -------------------------------------------
class CustomUser(AbstractUser):

    ROLE_CHOICES = [
        ('admin', 'ADMIN'),
        ('manager', 'MANAGER'),
        ('team_leader', 'TEAM LEADER'),
        ('employee', 'PRACOWNIK'),
        ('hr', 'HR'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='employee'
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # -------------------------------------------
    # PRACOWNIK → jego TEAM LEADER
    # TEAM LEADER → team_members (wszyscy z działu)
    # -------------------------------------------
    team_leader = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="team_members",  # TL.team_members.all()
        on_delete=models.SET_NULL
    )

    # -------------------------------------------
    # HELPERY
    # -------------------------------------------
    def is_admin(self):
        return self.role == 'admin'

    def is_manager(self):
        return self.role == 'manager'

    def is_team_leader(self):
        return self.role == 'team_leader'

    def is_employee(self):
        return self.role == 'employee'

    def __str__(self):
        dept = self.department if self.department else "BRAK DZIAŁU"
        return f"{self.username} ({self.get_role_display()} - {dept})"

    class Meta:
        verbose_name = "Użytkownik"
        verbose_name_plural = "Użytkownicy"
