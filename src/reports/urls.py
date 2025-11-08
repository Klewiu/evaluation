from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports_home, name='reports_home'),
    path('department/', views.department_report, name='department_report'),
    path('employee/', views.employee_report, name='employee_report'),
]