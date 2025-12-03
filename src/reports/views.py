from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from users.models import Department, CustomUser


from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from users.models import Department, CustomUser
from evaluations.models import EmployeeEvaluation
from surveys.models import Survey, SurveyResponse

from django.http import JsonResponse

from surveys.models import Survey, SurveyResponse, SurveyAnswer, Competency

from django.core.exceptions import PermissionDenied
from functools import wraps

def hr_or_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = request.user
        # jeśli nie jest zalogowany lub nie ma wymaganej roli
        if not user.is_authenticated or not (user.is_superuser or user.is_staff or getattr(user, 'role', '') == 'hr' or getattr(user, 'role', '') == 'manager'):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
@hr_or_admin_required
def get_surveys(request):
    department_id = request.GET.get("department")
    year = request.GET.get("year")
    selected_survey_id = request.GET.get("survey")
    surveys = []

    if department_id and year:
        surveys = Survey.objects.filter(department_id=department_id, year=year).order_by("name")

    return render(
        request,
        "reports/partials/_survey_options.html",
        {"surveys": surveys, "selected_survey_id": selected_survey_id},
    )

@login_required
@hr_or_admin_required
def reports_home(request):
    departments = Department.objects.all().order_by('name')
    employees = CustomUser.objects.filter(is_active=True).order_by('last_name', 'first_name')
    years = Survey.objects.values_list("year", flat=True).distinct().order_by("-year")

    selected_year = request.GET.get("year")
    selected_department_id = request.GET.get("department")
    selected_survey_id = request.GET.get("survey")

    # jeśli od razu chcemy pokazać ankiety przy załadowaniu strony
    surveys = []
    if selected_year and selected_department_id:
        surveys = Survey.objects.filter(
            year=selected_year,
            department_id=selected_department_id
        ).order_by("name")

    context = {
        "departments": departments,
        "employees": employees,
        "years": years,
        "surveys": surveys,
        "selected_year": selected_year,
        "selected_department_id": selected_department_id,
        "selected_survey_id": selected_survey_id,
    }

    return render(request, "reports/reports_home.html", context)

@login_required
@hr_or_admin_required
def department_report(request):
    department_id = request.GET.get("department")
    survey_id = request.GET.get("survey")  # teraz pobieramy wybraną ankietę
    selected_department = None
    current_survey = None
    chart_labels, chart_values = [], []

    if department_id and survey_id:
        selected_department = get_object_or_404(Department, id=department_id)
        current_survey = get_object_or_404(Survey, id=survey_id)
        employees = CustomUser.objects.filter(department=selected_department)

        for emp in employees:
            emp_response = (
                SurveyResponse.objects
                .filter(user=emp, survey=current_survey, status="submitted")
                .order_by('-created_at')
                .first()
            )
            if not emp_response:
                continue

            manager_answers = EmployeeEvaluation.objects.filter(employee_response=emp_response)
            if not manager_answers.exists():
                continue

            manager_scored = [a.scale_value for a in manager_answers if a.scale_value is not None]
            manager_total_points = sum(manager_scored)
            manager_max_points = len(manager_scored) * 10 if manager_scored else 0
            manager_percentage = round((manager_total_points / manager_max_points) * 100, 2) if manager_max_points else 0

            chart_labels.append(f"{emp.first_name} {emp.last_name}")
            chart_values.append(manager_percentage)

        if chart_labels:
            chart_data = sorted(zip(chart_labels, chart_values), key=lambda x: x[1], reverse=True)
            chart_labels, chart_values = zip(*chart_data)
            chart_labels = list(chart_labels)
            chart_values = list(chart_values)

    context = {
        "selected_department": selected_department,
        "current_survey": current_survey,
        "chart_labels": chart_labels,
        "chart_values": chart_values,
    }

    return render(request, "reports/department_report.html", context)

@login_required
@hr_or_admin_required
def department_radar_report(request):
    department_id = request.GET.get("department")
    year = request.GET.get("year")
    survey_id = request.GET.get("survey")
    score_type = request.GET.get("score_type", "employee")  # "employee" lub "manager"

    # 🔹 Mapa przyjaznych nazw
    SCORE_TYPE_DISPLAY = {
        "employee": "Ocena pracownika",
        "manager": "Ocena przełożonego",
    }
    score_type_display = SCORE_TYPE_DISPLAY.get(score_type, score_type)

    selected_department = None
    current_survey = None
    radar_labels = []
    radar_data = []
    avg_scores = []

    if department_id and survey_id:
        # Pobierz ankietę
        current_survey = get_object_or_404(Survey, id=survey_id)
        selected_department = current_survey.department

        # Pobierz wszystkich pracowników, którzy wzięli udział w ankiecie
        responses = SurveyResponse.objects.filter(
            survey=current_survey,
            user__department_id=department_id,
            status="submitted"
        )

        competencies = list(
            Competency.objects.filter(
                questions__surveyquestion__survey=current_survey
            ).distinct()
        )

        radar_labels = [c.name for c in competencies]

        for resp in responses:
            if score_type == "employee":
                answers = SurveyAnswer.objects.filter(response=resp)
            else:  # manager
                answers = EmployeeEvaluation.objects.filter(employee_response=resp)

            # Oblicz wynik dla każdej kompetencji
            scores = []
            for comp in competencies:
                comp_questions = current_survey.surveyquestion_set.filter(question__competency=comp)
                if comp_questions.exists():
                    max_total = len(comp_questions) * 10
                    total = sum(
                        [a.scale_value for a in answers if a.question in [q.question for q in comp_questions] and a.scale_value]
                    )
                    scores.append(round(total / max_total * 100, 2) if max_total else 0)
                else:
                    scores.append(0)

            radar_data.append({
                "employee": resp.user.get_full_name(),
                "scores": scores
            })

        # 🔹 Obliczenie średniej dla działu
        if radar_data:
            num_employees = len(radar_data)
            avg_scores = [
                round(sum(emp["scores"][i] for emp in radar_data) / num_employees, 2)
                for i in range(len(radar_labels))
            ]

    return render(request, "reports/department_radar_report.html", {
        "selected_department": selected_department,
        "current_survey": current_survey,
        "radar_labels": radar_labels,
        "radar_data": radar_data,
        "score_type": score_type,
        "score_type_display": score_type_display,  # <- teraz przyjazna nazwa
        "avg_scores": avg_scores
    })

@login_required
@hr_or_admin_required
def employee_report(request):
    employee_id = request.GET.get("employee")
    selected_employee = None
    chart_labels, chart_values = [], []

    if employee_id:
        selected_employee = get_object_or_404(CustomUser, id=employee_id)

        # pobierz wszystkie wypełnione ankiety pracownika, od najnowszej do najstarszej
        responses = SurveyResponse.objects.filter(user=selected_employee, status="submitted").order_by('-created_at')

        for response in responses:
            manager_answers = EmployeeEvaluation.objects.filter(employee_response=response)

            if not manager_answers.exists():
                continue

            manager_scored = [a.scale_value for a in manager_answers if a.scale_value is not None]
            manager_total_points = sum(manager_scored)
            manager_max_points = len(manager_scored) * 10 if manager_scored else 0
            manager_percentage = round((manager_total_points / manager_max_points) * 100, 2) if manager_max_points else 0

            # zamiast daty dodajemy nazwę ankiety
            chart_labels.append(response.survey.name)
            chart_values.append(manager_percentage)

        # konwersja na listy, aby JS poprawnie odczytał dane
        chart_labels = list(chart_labels)
        chart_values = list(chart_values)

    context = {
        "selected_employee": selected_employee,
        "chart_labels": chart_labels,
        "chart_values": chart_values,
    }
    return render(request, "reports/employee_report.html", context)


@login_required
@hr_or_admin_required
def latest_survey_report(request):
    labels = []
    manager_scores = []
    departments_checked = []

    departments = Department.objects.all()

    for dept in departments:
        employees = CustomUser.objects.filter(department=dept, role="employee")

        latest_response = (
            SurveyResponse.objects
            .filter(user__in=employees, status="submitted")
            .order_by('-created_at')
            .select_related('survey')
            .first()
        )

        if not latest_response:
            continue

        latest_survey = latest_response.survey
        departments_checked.append(f"{dept.name} ({latest_survey.name})")

        for emp in employees:
            emp_response = (
                SurveyResponse.objects
                .filter(user=emp, survey=latest_survey, status="submitted")
                .order_by('-created_at')
                .first()
            )
            if not emp_response:
                continue

            manager_answers = EmployeeEvaluation.objects.filter(employee_response=emp_response)
            if not manager_answers.exists():
                continue

            manager_values = [a.scale_value for a in manager_answers if a.scale_value is not None]
            if not manager_values:
                continue

            avg_manager_score = round((sum(manager_values) / len(manager_values)) * 10, 2)

            labels.append(f"{emp.first_name} {emp.last_name} ({dept.name})")
            manager_scores.append(avg_manager_score)

    # 🔹 sortowanie od najwyższej do najniższej oceny
    if labels and manager_scores:
        sorted_pairs = sorted(zip(manager_scores, labels), reverse=True)
        manager_scores, labels = map(list, zip(*sorted_pairs))  # zawsze listy
    else:
        manager_scores, labels = [], []

    context = {
        "chart_labels": labels,
        "manager_scores": manager_scores,
        "departments_checked": departments_checked,
    }

    return render(request, "reports/latest_survey_report.html", context)