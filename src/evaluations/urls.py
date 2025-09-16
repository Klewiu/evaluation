from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path("list/", views.evaluations_list, name="evaluations_list"),
    path('users/', include('users.urls')),
    path('surveys/', include('surveys.urls')),  # <- ważne!
   
]
