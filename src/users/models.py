from django.contrib.auth.models import AbstractUser
from django.db import models

# DZIAŁ W KTÓRYM PRACUJĄ PRACOWNICY
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Dział"
        verbose_name_plural = "Działy"
    
    

# MODEL UŻYTKOWNIKA Z DODATKOWYMI POLAMI
class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'ADMIN'),
        ('manager', 'MANAGER'),
        ('employee', 'PRACOWNIK'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)

    def is_admin(self):
        return self.role == 'admin'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()} - {self.department if self.department else 'BRAK DZIAŁU'})"

    class Meta:
        verbose_name = "Użytkownik"
        verbose_name_plural = "Użytkownicy"