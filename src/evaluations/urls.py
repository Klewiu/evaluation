from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path("manager/employees/", views.manager_employees, name="manager_employees"),
    path('users/', include('users.urls')),
    path('surveys/', include('surveys.urls')),  # <- ważne!
   
]
