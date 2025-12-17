# SEKCJA IMPORTÓW   
import os
import io
import base64
from functools import wraps

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.staticfiles.finders import find
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import Q, Exists, OuterRef
from django.contrib.auth import get_user_model

from surveys.models import Survey, SurveyResponse, SurveyAnswer, Competency
from users.models import CustomUser
from evaluations.models import EmployeeEvaluation, EmployeeEvaluationHR
from wkhtmltopdf.views import PDFTemplateView


# 1 ---- SEKCJA DEKORATORÓW I FUNKCJI POMOCNICZYCH

def hr_or_admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.role not in ['hr', 'admin']:
            raise PermissionDenied("Nie masz dostępu do tego widoku.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def employee_surveys_access_required(view_func):
    @wraps(view_func)
    def wrapper(request, user_id, *args, **kwargs):
        employee = get_object_or_404(CustomUser, pk=user_id)

        # ✅ ADMIN / HR / SUPERUSER → wszystko
        if request.user.role in ['admin', 'hr'] or request.user.is_superuser:
            return view_func(request, user_id, *args, **kwargs)

        # ✅ MANAGER → tylko swój dział
        if request.user.role == 'manager':
            if employee.department == request.user.department:
                return view_func(request, user_id, *args, **kwargs)
            raise PermissionDenied

        # ✅ TEAM LEADER → tylko jego przypisani pracownicy
        if request.user.role == 'team_leader':
            if employee.team_leader == request.user:
                return view_func(request, user_id, *args, **kwargs)
            raise PermissionDenied

        # ❌ EMPLOYEE → BRAK DOSTĘPU
        raise PermissionDenied

    return wrapper

def manager_or_privileged_access_required(view_func):
    def wrapper(request, response_id, *args, **kwargs):
        response = get_object_or_404(SurveyResponse, id=response_id)
        viewed_user = response.user  # osoba, której dotyczy ocena

        # 🔹 1. HR i Admin — pełen dostęp
        if request.user.role in ['hr', 'admin']:
            return view_func(request, response_id, *args, **kwargs)

        # 🔹 2. Manager — tylko pracownicy z jego działu
        if request.user.role == 'manager':
            if viewed_user.department == request.user.department:
                return view_func(request, response_id, *args, **kwargs)
            raise PermissionDenied

        # 🔹 3. Team Leader — dostęp do:
        #     ✔ własnej oceny
        #     ✔ ocen pracowników, którzy mają team_leader = request.user
        if request.user.role == 'team_leader':
            if viewed_user == request.user:
                return view_func(request, response_id, *args, **kwargs)

            if viewed_user.team_leader == request.user:
                return view_func(request, response_id, *args, **kwargs)

            raise PermissionDenied

        # 🔹 4. Pracownik — może zobaczyć tylko własną ocenę
        if request.user.role == 'employee':
            if viewed_user == request.user:
                return view_func(request, response_id, *args, **kwargs)
            raise PermissionDenied

        # 🔹 5. Inne role — brak dostępu
        raise PermissionDenied
    return wrapper

# 2 ----  SEKCJA WIDOKÓW 


# GŁÓWNY PANEL UŻYTKOWNIKA - to co widzi po zalogowaniu
@login_required
def home(request):
    user = request.user
    surveys_list = []

    if user.department:
        # filtrowanie ankiet w zależności od roli
        if user.role == 'employee':
            department_surveys = Survey.objects.filter(
                department=user.department,
                role__in=["employee"],
                created_at__gte=user.date_joined
            ).order_by('-created_at')
        elif user.role == 'manager':
            department_surveys = Survey.objects.filter(
                department=user.department,
                role__in=["manager" ],
                created_at__gte=user.date_joined
            ).order_by('-created_at')
        elif user.role == 'team_leader':
            department_surveys = Survey.objects.filter(
                department=user.department,
                role__in=["team_leader"],
                created_at__gte=user.date_joined
            ).order_by('-created_at')
        else:
            department_surveys = Survey.objects.none()

        for survey in department_surveys:
            response = SurveyResponse.objects.filter(survey=survey, user=user).first()

            manager_eval_status = None
            hr_eval_status = None
            show_manager_overview = False

            if response:
                # ocena managera (również gdy ocenia admin!)
                eval_qs = EmployeeEvaluation.objects.filter(employee_response=response)
                if eval_qs.exists():
                    statuses = eval_qs.values_list('status', flat=True)
                    if all(s == 'submitted' for s in statuses):
                        manager_eval_status = 'submitted'
                    elif any(s == 'draft' for s in statuses):
                        manager_eval_status = 'draft'

                # ocena HR
                try:
                    hr_eval = EmployeeEvaluationHR.objects.get(employee_response=response)
                    hr_eval_status = hr_eval.status
                except EmployeeEvaluationHR.DoesNotExist:
                    hr_eval_status = None

                # pokazujemy overview tylko gdy obie oceny zakończone
                show_manager_overview = (
                    manager_eval_status == 'submitted' and 
                    hr_eval_status == 'completed'
                )

            surveys_list.append({
                "survey": survey,
                "response": response,
                "manager_eval_status": manager_eval_status,
                "hr_eval_status": hr_eval_status,
                "show_manager_overview": show_manager_overview,
            })

    context = {"surveys": surveys_list}
    return render(request, 'evaluations/home.html', context)

# LISTA PRACONIKÓW dla managera / team leadera / admina / HR z statusami ankiet
@login_required
def manager_employees(request):
    user = request.user
    sort = request.GET.get("sort")  # sortowanie z URL

    employees = CustomUser.objects.none()

    # ------------------------------
    # Manager → dział
    # ------------------------------
    if user.role == "manager" and user.department:
        employees = CustomUser.objects.filter(
            department=user.department,
            role__in=["employee", "team_leader"],
            is_active=True
        )

    # ------------------------------
    # Team Leader → jego pracownicy
    # ------------------------------
    elif user.role == "team_leader":
        employees = CustomUser.objects.filter(
            team_leader=user,
            is_active=True
        )

    # ------------------------------
    # Admin / HR → wszyscy
    # ------------------------------
    elif user.role in ["admin", "hr"] or user.is_superuser:
        employees = CustomUser.objects.filter(
            role__in=["employee", "manager", "team_leader"],
            is_active=True
        )

    # ---------- SORTOWANIE ----------
    if sort == "department":
        employees = employees.order_by("department__name", "last_name")
    elif sort == "role":
        employees = employees.order_by("role", "last_name")
    else:
        employees = employees.order_by("last_name")  # domyślne sortowanie
    # ---------- LOGIKA ANKIET ----------
    employees_with_survey = []
    for emp in employees:
        latest_survey = Survey.objects.filter(
            department=emp.department,
            role__in=[emp.role, "both"]
        ).order_by("-created_at").first()

        has_survey = False
        manager_status = None
        hr_status = None

        if latest_survey:
            latest_survey_response = SurveyResponse.objects.filter(
                survey=latest_survey,
                user=emp
            ).first()

            if latest_survey_response:
                has_survey = latest_survey_response.status in ["submitted", "closed"]

                manager_eval_qs = EmployeeEvaluation.objects.filter(employee_response=latest_survey_response)
                if manager_eval_qs.exists():
                    statuses = manager_eval_qs.values_list('status', flat=True)
                    if all(s == 'submitted' for s in statuses):
                        manager_status = 'submitted'
                    elif any(s == 'draft' for s in statuses):
                        manager_status = 'draft'

                try:
                    hr_eval = EmployeeEvaluationHR.objects.get(employee_response=latest_survey_response)
                    hr_status = hr_eval.status
                except EmployeeEvaluationHR.DoesNotExist:
                    hr_status = None

        employees_with_survey.append({
            "employee": emp,
            "has_survey": has_survey,
            "manager_status": manager_status,
            "hr_status": hr_status,
            "latest_survey": latest_survey
        })

    return render(request, "evaluations/manager_employees.html", {
        "employees_with_survey": employees_with_survey,
        "sort": sort
    })

# LISTA ANKIET PRACOWNIKA z statusami ocen managera i HR (tutaj będą różne ankiety z różnych lat)
@login_required
@employee_surveys_access_required
def employee_surveys(request, user_id):
    employee = get_object_or_404(CustomUser, pk=user_id)
    
    # Filtrowanie ankiet po roli i po dacie zatrudnienia
    surveys = Survey.objects.filter(
        department=employee.department,
        role__in=[employee.role, "both"],
        created_at__gte=employee.date_joined  # tylko ankiety po zatrudnieniu
    ).order_by("-created_at")

    surveys_with_status = []
    for survey in surveys:
        try:
            response = SurveyResponse.objects.get(survey=survey, user=employee)
            has_survey = True
        except SurveyResponse.DoesNotExist:
            response = None
            has_survey = False

        # Status oceny managera
        manager_eval_status = None
        if response:
            manager_eval = EmployeeEvaluation.objects.filter(employee_response=response).first()
            if manager_eval:
                manager_eval_status = manager_eval.status

        # Status oceny HR
        hr_eval_status = None
        hr_eval = None
        if response:
            try:
                hr_eval = EmployeeEvaluationHR.objects.get(employee_response=response)
                hr_eval_status = hr_eval.status
            except EmployeeEvaluationHR.DoesNotExist:
                hr_eval_status = None

        surveys_with_status.append({
            "survey": survey,
            "has_survey": has_survey,
            "response": response,
            "manager_eval_status": manager_eval_status,  # draft / submitted / None
            "hr_eval_status": hr_eval_status,          # draft / completed / None
            "hr_eval": hr_eval,                        # obiekt HR jeśli istnieje
        })

    return render(request, "evaluations/employee_surveys.html", {
        "employee": employee,
        "surveys_with_status": surveys_with_status
    })

# OCENA PRACOWNIKA PRZEZ MANAGERA
@login_required
@manager_or_privileged_access_required
def manager_evaluate_employee(request, response_id):
    # Pobranie odpowiedzi pracownika
    employee_response = get_object_or_404(SurveyResponse, id=response_id)

    # Pobranie pytań i ocen
    employee_answers = SurveyAnswer.objects.filter(response=employee_response)
    manager_evals = EmployeeEvaluation.objects.filter(
        employee_response=employee_response,
        manager=request.user
    )
    manager_evals_dict = {e.question.id: e for e in manager_evals}
    scale_choices = list(range(0, 11))  # 0-10

    if request.method == "POST":
        save_type = request.POST.get("save_type", "draft")  # draft lub submitted

        # 🔹 Walidacja przy finalnym zapisie
        if save_type == "submitted":
            missing_questions = []
            for ans in employee_answers:
                if ans.scale_value is not None:  # pytanie punktowe
                    scale_value = request.POST.get(f'manager_scale_{ans.question.id}')
                    if not scale_value:
                        missing_questions.append(ans.question.text)

            if missing_questions:
                messages.error(
                    request,
                    "Musisz wypełnić wszystkie pola oceny managera."
                )
                return redirect(request.path)

        # 🔹 Zapis ocen
        for ans in employee_answers:
            scale_value = request.POST.get(f'manager_scale_{ans.question.id}')
            text_value = request.POST.get(f'text_{ans.question.id}', '')

            if scale_value or text_value:
                EmployeeEvaluation.objects.update_or_create(
                    employee_response=employee_response,
                    question=ans.question,
                    manager=request.user,
                    defaults={
                        'scale_value': int(scale_value) if scale_value else None,
                        'text_value': text_value,
                        'status': save_type
                    }
                )

        # 🔹 Przekierowanie po zapisaniu (draft i submitted w to samo miejsce)
        messages.success(
            request,
            "Oceny zostały zapisane." if save_type == "draft" else "Oceny zostały zakończone i zapisane."
        )
        return redirect('employee_surveys', user_id=employee_response.user.id)

    # GET — renderowanie formularza
    context = {
        'employee_response': employee_response,
        'employee_answers': employee_answers,
        'manager_evals_dict': manager_evals_dict,
        'scale_choices': scale_choices,
    }
    return render(request, 'evaluations/manager_evaluate.html', context)

# PODGLĄD OCENY PRACOWNIKA PRZEZ MANAGERA
@login_required
@manager_or_privileged_access_required
def manager_survey_overview(request, response_id):
    response_user = get_object_or_404(SurveyResponse, id=response_id)
    survey = response_user.survey
    viewed_user = response_user.user

    # Odpowiedzi użytkownika
    answers_user = SurveyAnswer.objects.filter(response=response_user)

    # Odpowiedzi managera
    answers_manager = EmployeeEvaluation.objects.filter(employee_response=response_user)

    # Kto oceniał
    manager_user = answers_manager.first().manager if answers_manager.exists() else None

    # Wykres radarowy
    radar_labels, radar_user_values, radar_manager_values = [], [], []
    competencies = Competency.objects.all()
    for comp in competencies:
        comp_questions = survey.surveyquestion_set.filter(question__competency=comp)
        if comp_questions.exists():
            max_total = len(comp_questions) * 10
            user_total = sum([
                a.scale_value for a in answers_user
                if a.question in [q.question for q in comp_questions] and a.scale_value is not None 
            ])
            manager_total = sum([
                a.scale_value for a in answers_manager
                if a.question in [q.question for q in comp_questions] and a.scale_value is not None
            ])
            radar_labels.append(comp.name)
            radar_user_values.append(round(user_total / max_total * 100, 2) if max_total else 0)
            radar_manager_values.append(round(manager_total / max_total * 100, 2) if max_total else 0)

    radar_data = list(zip(radar_labels, radar_user_values, radar_manager_values))
    scale_range = range(0, 11)

    # Suma punktów managera
    manager_scored = [a.scale_value for a in answers_manager if a.scale_value is not None]
    manager_total_points = sum(manager_scored)
    manager_max_points = len(manager_scored) * 10 if manager_scored else 0
    manager_percentage = round((manager_total_points / manager_max_points) * 100, 2) if manager_max_points else 0
    show_radar = len(radar_labels) >= 3

    # 🔹 Pobranie komentarza HR jeśli istnieje i jest completed
    hr_comment = None
    hr_comment_user = None
    hr_comment_date = None
    try:
        hr_eval = EmployeeEvaluationHR.objects.get(employee_response=response_user)
        if hr_eval.status == 'completed':
            hr_comment = hr_eval.comment
            hr_comment_user = hr_eval.created_by  # osoba która dodała komentarz
            hr_comment_date = hr_eval.completed_at
    except EmployeeEvaluationHR.DoesNotExist:
        pass

    return render(request, 'evaluations/manager_survey_overview.html', {
        "survey": survey,
        "viewed_user": viewed_user,
        "answers_user": answers_user,
        "answers_manager": answers_manager,
        "radar_labels": radar_labels,
        "radar_user_values": radar_user_values,
        "radar_manager_values": radar_manager_values,
        "radar_data": radar_data,
        "manager_user": manager_user,
        "scale_range": scale_range,
        "manager_total_points": manager_total_points,
        "manager_max_points": manager_max_points,
        "manager_percentage": manager_percentage,
        "show_radar": show_radar,
        "hr_comment": hr_comment,
        "hr_comment_user": hr_comment_user,
        "hr_comment_date": hr_comment_date,
    })

CustomUser = get_user_model()

# PDF Z PODGLĄDEM OCENY MANAGERA + WYKRESY
class ManagerSurveyOverviewPDFView(LoginRequiredMixin, PDFTemplateView):
    template_name = "evaluations/manager_survey_overview_pdf.html"

    cmd_options = {
        'footer-right': 'Strona [page] z [topage]',
        'footer-font-size': '8',
        'footer-spacing': '5',
        'margin-bottom': '15mm',
    }

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ['manager', 'team_leader', 'hr', 'admin'] and not request.user.is_superuser:
            raise PermissionDenied("Nie masz dostępu do tego pliku PDF.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        
        # Pobranie obiektu odpowiedzi
        survey_response = self.get_response()
        survey_name = slugify(survey_response.survey.name)
        user_full_name = slugify(survey_response.user.get_full_name())

        filename = f"{survey_name}_{user_full_name}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Type'] = 'application/pdf'
        return response


    def get_response(self):
        response_id = self.kwargs.get("response_id")
        return get_object_or_404(SurveyResponse, pk=response_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        response = self.get_response()

        # Odpowiedzi pracownika i managera
        answers_user = response.answers.all()
        answers_manager = EmployeeEvaluation.objects.filter(employee_response=response)

        # Wyliczenie kompetencji
        labels, user_values, manager_values = [], [], []
        competencies = response.survey.questions.values_list("competency__name", flat=True).distinct()
        competencies = [c for c in competencies if c]

        for comp_name in competencies:
            comp_questions = response.survey.questions.filter(competency__name=comp_name)
            max_total = comp_questions.count() * 10
            user_total = sum(a.scale_value for a in answers_user if a.question in comp_questions and a.scale_value is not None)
            manager_total = sum(a.scale_value for a in answers_manager if a.question in comp_questions and a.scale_value is not None)
            labels.append(comp_name)
            user_values.append(round(user_total / max_total * 100, 2) if max_total else 0)
            manager_values.append(round(manager_total / max_total * 100, 2) if max_total else 0)

            if len(labels) >= 3:
                radar_image = self._generate_radar_chart_user_manager(labels, user_values, manager_values)
                show_radar = True
            else:
                radar_image = None
                show_radar = False

        radar_data = list(zip(labels, user_values, manager_values))

        # START: POPRAWIONE POBRANIE LOGO JAKO BASE64
        logo_base64 = None
        logo_path = find("ats.jpg")
        if logo_path and os.path.exists(logo_path):
            try:
                with open(logo_path, "rb") as f:
                    logo_base64 = base64.b64encode(f.read()).decode("utf-8")
            except Exception as e:
                print(f"Błąd podczas kodowania logo do base64: {e}")
        else:
            print("NIE ZNALEZIONO LOGO: ats.jpg nie znaleziono w ścieżkach statycznych!")
        # KONIEC: POPRAWIONE POBRANIE LOGO JAKO BASE64

        # 🔹 SUMA PUNKTÓW – tylko oceny managera
        manager_scored = [a.scale_value for a in answers_manager if a.scale_value is not None]
        manager_total_points = sum(manager_scored)
        manager_max_points = len(manager_scored) * 10 if manager_scored else 0
        manager_percentage = round((manager_total_points / manager_max_points) * 100, 2) if manager_max_points else 0

        context.update({
            "response": response,
            "answers_user": answers_user,
            "answers_manager": answers_manager,
            "radar_image": radar_image,
            "radar_data": radar_data,
            "show_radar": True,
            "scale_range": range(0, 11),
            "logo_base64": logo_base64,
            "manager_total_points": manager_total_points,
            "manager_max_points": manager_max_points,
            "manager_percentage": manager_percentage,
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

        fig, ax = plt.subplots(figsize=(7,7), subplot_kw=dict(polar=True))  # większy wykres
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_xticks(angles)
        ax.set_xticklabels(labels, fontsize=12)
        ax.set_ylim(0, 100)
        ax.set_yticks(range(0, 101, 10))  # linie co 10%
        ax.set_rlabel_position(0)
        ax.yaxis.grid(True, linestyle='--', linewidth=0.5)  # poziome linie pomocnicze
        ax.xaxis.grid(False) 

        # Linie siatki
        for angle in angles:
            ax.plot([angle, angle], [0, 100], color='gray', linestyle='dashed', linewidth=0.5)

        # Wartości pracownika
        ax.plot(angles_closed, user_values_closed, color='#0d6efd', linewidth=2.5, label='Pracownik')  # niebieski
        ax.fill(angles_closed, user_values_closed, '#0d6efd', alpha=0.15)

        # Wartości managera
        if manager_values_closed:
            ax.plot(angles_closed, manager_values_closed, color='#000000', linewidth=2.5, label='Manager')  # czarny
            ax.fill(angles_closed, manager_values_closed, '#000000', alpha=0.15)

        # Legenda większa i czytelna
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=12, frameon=False)

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return img_base64

# KOMENTARZ HR DO OCENY PRACOWNIKA I MANAGERA
# Po zakończeniu oceny managera, HR może dodać swój komentarz do oceny pracownika i dopiero wtedy pracownik zobaczy pełną ocenę
@login_required
@hr_or_admin_required
def hr_comment_employee(request, response_id):
    if request.user.role not in ['hr', 'admin']:
        messages.error(request, "Brak dostępu do tego widoku.")
        return redirect('home')

    response = get_object_or_404(SurveyResponse, id=response_id)
    survey = response.survey
    viewed_user = response.user

    # Pobranie odpowiedzi pracownika i managera
    answers_user = response.answers.all()
    answers_manager = EmployeeEvaluation.objects.filter(employee_response=response)

    # Pobranie lub utworzenie komentarza HR
    hr_eval, created = EmployeeEvaluationHR.objects.get_or_create(employee_response=response)

    if request.method == 'POST':
        hr_comment = request.POST.get('hr_comment', '').strip()
        hr_eval.comment = hr_comment

        action = request.POST.get('action')
        if action == 'draft':
            hr_eval.status = 'draft'
            hr_eval.completed_at = None
            messages.success(request, "Komentarz HR został zapisany jako roboczy.")
        elif action == 'completed':
            hr_eval.mark_completed(user=request.user)
            messages.success(request, "Komentarz HR został zapisany i wysłany do pracownika.")

        hr_eval.save()
        return redirect('employee_surveys', user_id=viewed_user.id)

    scale_range = range(0, 11)

    context = {
        'survey': survey,
        'viewed_user': viewed_user,
        'answers_user': answers_user,
        'answers_manager': answers_manager,
        'scale_range': scale_range,
        'hr_comment': hr_eval.comment,
        'manager_user': answers_manager.first().manager if answers_manager.exists() else None,
        'show_radar': False,
        'hr_eval': hr_eval,  # dodajemy cały obiekt HR
    }

    return render(request, 'evaluations/hr_comment_survey.html', context)