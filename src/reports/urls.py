from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports_home, name='reports_home'),
    path('department/', views.department_report, name='department_report'),
    path('employee/', views.employee_report, name='employee_report'),
    path('latest-survey-report/', views.latest_survey_report, name='latest_survey_report'),
    path('get-surveys/', views.get_surveys, name='get_surveys'),
    path('department/radar/', views.department_radar_report, name='department_radar_report'),
]