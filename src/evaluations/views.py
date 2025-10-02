from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from surveys.models import Survey, SurveyResponse

from surveys.models import Survey, SurveyResponse


from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from users.models import CustomUser
from surveys.models import Survey, SurveyResponse

from django.db.models import Q

@login_required
def home(request):
    user = request.user
    surveys_list = []

    if user.department:
        # Filtrowanie ankiet zależnie od roli
        if user.role == 'employee':
            department_surveys = Survey.objects.filter(
                department=user.department,
                role__in=["employee", "both"]
            ).order_by('-created_at')

        elif user.role == 'manager':
            department_surveys = Survey.objects.filter(
                department=user.department,
                role__in=["manager", "both"]
            ).order_by('-created_at')

        else:
            department_surveys = Survey.objects.none()

        # Sparuj ankiety z ewentualnymi odpowiedziami użytkownika
        for survey in department_surveys:
            try:
                response = SurveyResponse.objects.get(survey=survey, user=user)
            except SurveyResponse.DoesNotExist:
                response = None

            surveys_list.append({
                "survey": survey,
                "response": response,
            })

    context = {
        "surveys": surveys_list,
    }
    return render(request, 'evaluations/home.html', context)

@login_required
def manager_employees(request):
    user = request.user
    employees_with_survey = []

    # Manager → tylko pracownicy jego działu
    if user.role == "manager" and user.department:
        employees = CustomUser.objects.filter(
            department=user.department,
            role="employee"
        )

    # Admin lub HR → wszyscy użytkownicy (managerowie i pracownicy)
    elif user.role in ["admin", "hr"] or user.is_superuser:
        employees = CustomUser.objects.filter(
            role__in=["employee", "manager"]
        )
    
    else:
        employees = CustomUser.objects.none()  # inni nie mają dostępu

    for emp in employees:
        # Pobierz najnowszą ankietę pracownika
        latest_survey_response = SurveyResponse.objects.filter(
            user=emp
        ).order_by("-created_at").first()  # najnowsza według created_at

        has_survey = False
        if latest_survey_response:
            has_survey = latest_survey_response.status in ["submitted", "closed"]

        employees_with_survey.append({
            "employee": emp,
            "has_survey": has_survey,
            "latest_survey": latest_survey_response
        })

    context = {
        "employees_with_survey": employees_with_survey,
    }
    return render(request, "evaluations/manager_employees.html", context)