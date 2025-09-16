from django.urls import path
from . import views

urlpatterns = [
    path("", views.surveys_list, name="surveys_list"),
]