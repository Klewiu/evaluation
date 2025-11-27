from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from users.models import Department, CustomUser


from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from users.models import Department, CustomUser
from evaluations.models import EmployeeEvaluation
from surveys.models import Survey, SurveyResponse

@login_required
def reports_home(request):
    departments = Department.objects.all().order_by('name')
    employees = CustomUser.objects.filter(is_active=True).order_by('last_name', 'first_name')
    years = (
        Survey.objects.values_list("year", flat=True)
        .distinct()
        .order_by("-year")
    )
    context = {
        'departments': departments,
        'employees': employees,
        "years": years,
    }
    return render(request, 'reports/reports_home.html', context)

@login_required
def department_report(request):
    department_id = request.GET.get("department")
    year = request.GET.get("year")  # << NOWOŚĆ
    selected_department = None
    chart_labels, chart_values = [], []
    current_survey = None

    if department_id:
        selected_department = get_object_or_404(Department, id=department_id)
        employees = CustomUser.objects.filter(department=selected_department, role="employee")

        # Filtrowanie ankiet po dziale + roku (jeśli podany)
        survey_filter = Survey.objects.filter(department=selected_department)

        if year:
            survey_filter = survey_filter.filter(year=year)

        # Wybierz najnowszą ankietę zgodną z filtrem
        latest_survey = survey_filter.order_by("-year", "-created_at").first()

        if latest_survey:
            current_survey = latest_survey

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

                manager_scored = [a.scale_value for a in manager_answers if a.scale_value]
                manager_total_points = sum(manager_scored)
                manager_max_points = len(manager_scored) * 10 if manager_scored else 0
                manager_percentage = round((manager_total_points / manager_max_points) * 100, 2) if manager_max_points else 0

                chart_labels.append(f"{emp.first_name} {emp.last_name}")
                chart_values.append(manager_percentage)

            # Sortowanie wyników
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

            manager_scored = [a.scale_value for a in manager_answers if a.scale_value]
            manager_total_points = sum(manager_scored)
            manager_max_points = len(manager_scored) * 10 if manager_scored else 0
            manager_percentage = round((manager_total_points / manager_max_points) * 100, 2) if manager_max_points else 0

            chart_labels.append(response.created_at.strftime("%Y-%m-%d"))  # data ankiety
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