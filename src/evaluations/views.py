from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from surveys.models import Survey, SurveyResponse, Competency

from surveys.models import Survey, SurveyResponse, SurveyAnswer


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from users.models import CustomUser
from surveys.models import Survey, SurveyResponse

from django.db.models import Q,Exists, OuterRef

from .models import EmployeeEvaluation

from django.contrib.auth.mixins import LoginRequiredMixin
from wkhtmltopdf.views import PDFTemplateView
import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from django.shortcuts import get_object_or_404
from surveys.models import SurveyResponse, SurveyAnswer 
from evaluations.models import EmployeeEvaluation  # dostosuj importy
from django.contrib.auth import get_user_model

from evaluations.models import EmployeeEvaluation  # dodaj import

from django.core.exceptions import PermissionDenied



from django.core.exceptions import PermissionDenied

def can_view_manager_evaluation(request_user, survey_response):
    target_user = survey_response.user

    if request_user.role == "employee":
        # pracownik może zobaczyć tylko swoje własne odpowiedzi
        if target_user != request_user:
            raise PermissionDenied("Nie masz dostępu do tej oceny.")

    elif request_user.role == "manager":
        # manager może zobaczyć tylko pracowników swojego działu
        if target_user.department != request_user.department or target_user.role != "employee":
            raise PermissionDenied("Nie masz dostępu do tej oceny.")

    elif request_user.role in ["admin", "hr"] or request_user.is_superuser:
        # admin i HR wszystko widzą
        pass
    else:
        raise PermissionDenied("Nie masz dostępu do tej oceny.")

@login_required
def home(request):
    user = request.user
    surveys_list = []

    if user.department:
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

        for survey in department_surveys:
            try:
                response = SurveyResponse.objects.get(survey=survey, user=user)
            except SurveyResponse.DoesNotExist:
                response = None

            # Sprawdzenie ocen managera
            if response:
                if user.role == 'employee':
                    # pracownik widzi wszystkie oceny managerów
                    show_manager_evaluation = EmployeeEvaluation.objects.filter(
                        employee_response=response
                    ).exists()
                elif user.role == 'manager':
                    # manager widzi tylko jeśli ocenił admin
                    show_manager_evaluation = EmployeeEvaluation.objects.filter(
                        employee_response=response,
                        manager__role='admin'  # zakładam, że CustomUser ma pole role
                    ).exists()
                else:
                    show_manager_evaluation = False
            else:
                show_manager_evaluation = False

            surveys_list.append({
                "survey": survey,
                "response": response,
                "has_manager_evaluation": show_manager_evaluation
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
        # Pobierz najnowszą ankietę dla działu i roli pracownika
        latest_survey = Survey.objects.filter(
            department=emp.department,
            role__in=[emp.role, "both"]
        ).order_by("-created_at").first()

        has_survey = False
        manager_evaluated = False  # dodajemy status oceny przez managera

        if latest_survey:
            # Sprawdź, czy pracownik wypełnił tę ankietę
            latest_survey_response = SurveyResponse.objects.filter(
                survey=latest_survey,
                user=emp
            ).first()

            if latest_survey_response:
                has_survey = latest_survey_response.status in ["submitted", "closed"]

                # Sprawdź, czy manager ocenił ankietę
                manager_evaluated = EmployeeEvaluation.objects.filter(
                    employee_response=latest_survey_response
                ).exists()

        employees_with_survey.append({
            "employee": emp,
            "has_survey": has_survey,
            "manager_evaluated": manager_evaluated,
            "latest_survey": latest_survey
        })

    context = {
        "employees_with_survey": employees_with_survey,
    }
    return render(request, "evaluations/manager_employees.html", context)


@login_required
def employee_surveys(request, user_id):
    employee = get_object_or_404(CustomUser, pk=user_id)
    
    surveys = Survey.objects.filter(
        department=employee.department,
        role__in=[employee.role, "both"]
    ).order_by("-created_at")

    surveys_with_status = []
    for survey in surveys:
        try:
            response = SurveyResponse.objects.get(survey=survey, user=employee)
            has_survey = response.status in ["submitted", "closed"]
        except SurveyResponse.DoesNotExist:
            response = None
            has_survey = False

        # Sprawdzenie, czy **jakikolwiek manager ocenił ankietę**
        manager_evaluated = False
        if response:
            manager_evaluated = EmployeeEvaluation.objects.filter(
                employee_response=response
            ).exists()

        surveys_with_status.append({
            "survey": survey,
            "has_survey": has_survey,
            "response": response,
            "manager_evaluated": manager_evaluated,
        })

    return render(request, "evaluations/employee_surveys.html", {
        "employee": employee,
        "surveys_with_status": surveys_with_status
    })


@login_required
def manager_evaluate_employee(request, response_id):
    employee_response = get_object_or_404(SurveyResponse, id=response_id)
    employee_answers = SurveyAnswer.objects.filter(response=employee_response)
    
    manager_evals = EmployeeEvaluation.objects.filter(employee_response=employee_response)
    manager_evals_dict = {e.question.id: e for e in manager_evals}
    # Skala ocen od 1 do 10
    scale_choices = list(range(1, 11))

    if request.method == "POST":
        for ans in employee_answers:
            scale = request.POST.get(f'manager_scale_{ans.question.id}')
            text = request.POST.get(f'text_{ans.question.id}', '')
            
            if scale or text:
                EmployeeEvaluation.objects.update_or_create(
                    employee_response=employee_response,
                    question=ans.question,
                    manager=request.user,
                    defaults={
                        'scale_value': int(scale) if scale else None,
                        'text_value': text
                    }
                )
        return redirect('manager_employees')  

    return render(request, 'evaluations/manager_evaluate.html', {
        'employee_response': employee_response,
        'employee_answers': employee_answers,
        'manager_evals_dict': manager_evals_dict,
        'scale_choices': scale_choices,
    })


@login_required
def manager_survey_overview(request, response_id):
    response_user = get_object_or_404(SurveyResponse, id=response_id)
    survey = response_user.survey
    viewed_user = response_user.user
    survey_response = get_object_or_404(SurveyResponse, id=response_id)
    
    # sprawdzenie uprawnień
    can_view_manager_evaluation(request.user, survey_response)
    # Odpowiedzi użytkownika
    answers_user = SurveyAnswer.objects.filter(response=response_user)

    # Odpowiedzi managera
    answers_manager = EmployeeEvaluation.objects.filter(employee_response=response_user)

    # Przygotowanie wykresu radarowego
    radar_labels, radar_user_values, radar_manager_values = [], [], []

    competencies = Competency.objects.all()
    for comp in competencies:
        comp_questions = survey.surveyquestion_set.filter(question__competency=comp)
        if comp_questions.exists():
            max_total = sum([10 for q in comp_questions])
            user_total = sum([a.scale_value for a in answers_user if a.question in [q.question for q in comp_questions] and a.scale_value])
            manager_total = sum([a.scale_value for a in answers_manager if a.question in [q.question for q in comp_questions] and a.scale_value])
            radar_labels.append(comp.name)
            radar_user_values.append(round(user_total / max_total * 100, 2) if max_total else 0)
            radar_manager_values.append(round(manager_total / max_total * 100, 2) if max_total else 0)

    radar_data = list(zip(radar_labels, radar_user_values, radar_manager_values))

    return render(request, 'evaluations/manager_survey_overview.html', {
        "survey": survey,
        "viewed_user": viewed_user,
        "answers_user": answers_user,
        "answers_manager": answers_manager,
        "radar_labels": radar_labels,
        "radar_user_values": radar_user_values,
        "radar_manager_values": radar_manager_values,
        "radar_data": radar_data,
    })

CustomUser = get_user_model()

class ManagerSurveyOverviewPDFView(LoginRequiredMixin, PDFTemplateView):
    template_name = "evaluations/manager_survey_overview_pdf.html"

    def get_response(self):
        response_id = self.kwargs.get("response_id")
        return get_object_or_404(SurveyResponse, pk=response_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        response = self.get_response()

        # Odpowiedzi pracownika
        answers_user = response.answers.all()

        # Odpowiedzi managera — przypisane do tego response i aktualnego managera
        answers_manager = EmployeeEvaluation.objects.filter(employee_response=response)

        # Wyliczenie kompetencji
        labels, user_values, manager_values = [], [], []

        competencies = response.survey.questions.values_list("competency__name", flat=True).distinct()
        competencies = [c for c in competencies if c]

        for comp_name in competencies:
            comp_questions = response.survey.questions.filter(competency__name=comp_name)
            max_total = comp_questions.count() * 10

            user_total = sum(
                a.scale_value for a in answers_user if a.question in comp_questions and a.scale_value is not None
            )
            manager_total = sum(
                a.scale_value for a in answers_manager if a.question in comp_questions and a.scale_value is not None
            )

            labels.append(comp_name)
            user_values.append(round(user_total / max_total * 100, 2) if max_total else 0)
            manager_values.append(round(manager_total / max_total * 100, 2) if max_total else 0)

        # Wygenerowanie wspólnego radaru
        radar_image = self._generate_radar_chart_user_manager(labels, user_values, manager_values)

        # Dane do tabeli pod wykresem
        radar_data = list(zip(labels, user_values, manager_values))

        context.update({
            "response": response,
            "answers_user": answers_user,
            "answers_manager": answers_manager,
            "radar_image": radar_image,
            "radar_data": radar_data,
        })

        return context

    def _generate_radar_chart_user_manager(self, labels, user_values, manager_values):
        if not labels:
            return None

        N = len(labels)
        angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
        angles_closed = angles + [angles[0]]
        user_values_closed = user_values + [user_values[0]]
        manager_values_closed = manager_values + [manager_values[0]] if manager_values else None

        fig, ax = plt.subplots(figsize=(6,6), subplot_kw=dict(polar=True))
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_xticks(angles)
        ax.set_xticklabels(labels)
        ax.set_ylim(0, 100)
        ax.set_rlabel_position(0)
        ax.grid(True)

        # Linie siatki
        for angle in angles:
            ax.plot([angle, angle], [0, 100], color='gray', linestyle='dashed', linewidth=0.5)

        # Wartości pracownika
        ax.plot(angles_closed, user_values_closed, color='blue', linewidth=2, label='Pracownik')
        ax.fill(angles_closed, user_values_closed, 'blue', alpha=0.1)

        # Wartości managera
        if manager_values_closed:
            ax.plot(angles_closed, manager_values_closed, color='red', linewidth=2, label='Manager')
            ax.fill(angles_closed, manager_values_closed, 'red', alpha=0.1)

        ax.legend(loc='upper right', bbox_to_anchor=(1.15, 1.15))

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return img_base64
