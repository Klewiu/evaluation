from django.urls import path
from . import views

urlpatterns = [

    # Główny widok komponentu ankiet (dashboard)
    path("", views.surveys_home, name="surveys_home"),

    # ŚCIEŻKI PYTAŃ
    path("questions/", views.questions_list, name="questions_list"),
    path("questions/add/", views.question_add, name="question_add"),
    path("questions/<int:pk>/edit/", views.question_edit, name="question_edit"),
    path("questions/<int:pk>/delete/", views.question_delete, name="question_delete"),

    # ŚCIEŻKI KOMPETENCJI
    path("competencies/", views.competencies_list, name="competencies_list"),
    path("competencies/add/", views.competency_add, name="competency_add"),
    path("competencies/<int:pk>/edit/", views.competency_edit, name="competency_edit"),
    path("competencies/<int:pk>/delete/", views.competency_delete, name="competency_delete"),

    # ŚCIEŻKI ANKIET
    path("list/", views.surveys_list, name="surveys_list"),

    path('survey/add/', views.survey_add, name='survey_add'),
    path('survey/<int:pk>/edit/', views.survey_edit, name='survey_edit'),
    path('survey/<int:pk>/delete/', views.survey_delete, name='survey_delete'),
    path('survey/<int:pk>/preview/', views.survey_preview, name='survey_preview'),

    # HTMX pytania
    path("load-questions/", views.load_questions, name="load_questions"),
]