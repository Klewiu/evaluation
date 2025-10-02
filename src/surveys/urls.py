from django.urls import path
from . import views
from .views import SurveyPDFView, survey_result

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

    # ZARZĄDZANIE ANKIETAMI
    path('survey/add/', views.survey_add, name='survey_add'),
    path('survey/<int:pk>/edit/', views.survey_edit, name='survey_edit'),
    path('survey/<int:pk>/delete/', views.survey_delete, name='survey_delete'),
    path('survey/<int:pk>/preview/', views.survey_preview, name='survey_preview'),
    path("survey/<int:pk>/save-order/", views.save_question_order, name="save_question_order"),
    
    # WYPEŁNIANIE ANKIETY
    path("survey/<int:pk>/fill/", views.survey_fill, name="survey_fill"),
    path('survey/<int:pk>/submit/', views.survey_submit, name='survey_submit'),
    # Podgląd wyników dla pracownika (prywatny)
    path('survey/<int:survey_id>/result/', survey_result, name='survey_result'),
    # Podgląd wyników dla managera/admina (dla wybranego użytkownika)
    path('survey/<int:survey_id>/result/<int:user_id>/', survey_result, name='survey_result_for_user'),
    
    path('survey/<int:pk>/edit-response/', views.survey_edit_response, name='survey_edit_response'),

    # PDF
    path('survey/<int:pk>/pdf/', SurveyPDFView.as_view(), name='survey_pdf'),

    # HTMX pytania
    path("load-questions/", views.load_questions, name="load_questions"),
]