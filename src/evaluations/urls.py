from django.urls import path, include
from . import views
from surveys.views import survey_result, SurveyPDFView

urlpatterns = [
    path('', views.home, name='home'),
    path('users/', include('users.urls')),
    path('surveys/', include('surveys.urls')),

     path("manager/employees/", views.manager_employees, name="manager_employees"),

    path('employee/<int:user_id>/surveys/', views.employee_surveys, name='employee_surveys'),

    # Podgląd wyników ankiety (dla admin/manager)
    path('survey/<int:survey_id>/result/', survey_result, name='survey_result'),
    # PDF ankiety
    path('survey/<uuid:slug>/pdf/<int:user_id>/', SurveyPDFView.as_view(), name='survey_pdf'),
    # Ocena pracownika przez managera
    path('evaluate/<int:response_id>/', views.manager_evaluate_employee, name='manager_evaluate_employee'),
    # Podgląd oceny pracownika przez managera
    path('manager/survey_overview/<int:response_id>/', views.manager_survey_overview, name='manager_survey_overview'),
    # PDF z podglądem oceny managera + wykresami
   path('manager/survey_overview/pdf/<int:response_id>/', views.ManagerSurveyOverviewPDFView.as_view(), name='manager_survey_overview_pdf'),
    # Komentarz HR do oceny pracownika i managera
    path('hr-comment/<int:response_id>/', views.hr_comment_employee, name='hr_comment_employee'),




]
    
