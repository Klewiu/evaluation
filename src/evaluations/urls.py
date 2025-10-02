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
    path('survey/<int:survey_id>/pdf/<int:user_id>/', SurveyPDFView.as_view(), name='survey_pdf'),
    
]
