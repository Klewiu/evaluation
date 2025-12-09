import json, os
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.db.models import Q

from django.utils import timezone

from users.models import Department
from .models import Question, Competency, Survey, SurveyQuestion, SurveyResponse, SurveyAnswer
from .forms import QuestionForm, CompetencyForm, SurveyForm 


from django.contrib.auth.mixins import LoginRequiredMixin
from wkhtmltopdf.views import PDFTemplateView
import io
import base64
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import numpy as np
from django.views.generic import TemplateView

from users.models import CustomUser
# KOMPETENCJE

from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from functools import wraps

def manager_or_privileged_access_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        current = request.user
        response = None

        # Pobranie slug lub survey_id (dla kompatybilności)
        slug = kwargs.get('slug')
        survey_id = kwargs.get('survey_id') or kwargs.get('pk')

        user_id = kwargs.get('user_id')

        # Jeśli mamy slug, pobieramy Survey
        if slug:
            survey = get_object_or_404(Survey, slug=slug)
            survey_id = survey.id

        # Pobranie response
        if 'response_id' in kwargs:
            response = get_object_or_404(SurveyResponse, id=kwargs.get('response_id'))
        elif survey_id and user_id:
            response = SurveyResponse.objects.filter(survey_id=survey_id, user_id=user_id).first()
            if not response:
                raise PermissionDenied("Brak odpowiedzi dla tego użytkownika")
        elif survey_id:
            response = SurveyResponse.objects.filter(survey_id=survey_id, user=current).first()
            if not response:
                raise PermissionDenied("Brak Twojej ankiety dla tej ankiety")
        else:
            raise PermissionDenied("Brak danych do weryfikacji dostępu")

        target_user = response.user

        # --- ADMIN / HR / SUPERUSER ---
        if current.role in ['admin', 'hr'] or current.is_superuser:
            return view_func(request, *args, **kwargs)

        # --- MANAGER ---
        if current.role == 'manager':
            if target_user.department_id == current.department_id:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied

        # --- TEAM LEADER ---
        if current.role == 'team_leader':
            if target_user == current or target_user.team_leader_id == current.id:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied

        # --- PRACOWNIK ---
        if current.role == 'employee':
            if target_user == current:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied

        raise PermissionDenied

    return wrapper

# Kompetencje
# Lista kompetencji (wszystkie w jednym worku)
@login_required
def competencies_list(request):
    competencies = Competency.objects.all()
    context = {
        "competencies": competencies,
    }
    return render(request, "surveys/competencies_list.html", context)


# Dodawanie kompetencji
@login_required
def competency_add(request):
    if request.method == "POST":
        form = CompetencyForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("competencies_list")
    else:
        form = CompetencyForm()
    return render(request, "surveys/competency_add.html", {"form": form})


# Edycja kompetencji
@login_required
def competency_edit(request, pk):
    competency = get_object_or_404(Competency, pk=pk)
    if request.method == "POST":
        form = CompetencyForm(request.POST, instance=competency)
        if form.is_valid():
            form.save()
            return redirect("competencies_list")
    else:
        form = CompetencyForm(instance=competency)

    return render(
        request,
        "surveys/competency_edit.html",
        {"form": form, "competency": competency},
    )


# Usuwanie kompetencji
@login_required
@require_POST
def competency_delete(request, pk):
    competency = get_object_or_404(Competency, pk=pk)
    competency.delete()
    return redirect("competencies_list")

# PYTANIA

# Pytania
# --- Wyświetlanie listy pytań ---
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import Question
from users.models import Department

from collections import OrderedDict
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Question, Department

from collections import OrderedDict
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Question, Department

@login_required
def questions_list(request):
    department_id = request.GET.get('department_id')
    selected_role = request.GET.get('role')  # 'manager', 'employee', 'both'
    departments = Department.objects.all().order_by('name')  # alfabetyczna kolejność działów

    # Funkcja do filtrowania po roli
    def filter_by_role(queryset):
        if selected_role and selected_role != 'both':
            return queryset.filter(Q(role='both') | Q(role=selected_role))
        return queryset

    if department_id and department_id != 'all':
        filtered_department = get_object_or_404(Department, id=department_id)
        department_questions = OrderedDict()

        dept_questions = Question.objects.filter(
            departments=filtered_department,
            is_active=True
        ).order_by('competency__name', 'text')
        dept_questions = filter_by_role(dept_questions)

        if dept_questions.exists():
            department_questions[filtered_department] = dept_questions

        unassigned_questions = Question.objects.filter(
            departments__isnull=True,
            is_active=True
        ).order_by('competency__name', 'text')
        unassigned_questions = filter_by_role(unassigned_questions)

    else:
        department_questions = OrderedDict()
        for dept in departments:
            dept_questions = Question.objects.filter(
                departments=dept,
                is_active=True
            ).order_by('competency__name', 'text')
            dept_questions = filter_by_role(dept_questions)
            if dept_questions.exists():
                department_questions[dept] = dept_questions

        unassigned_questions = Question.objects.filter(
            departments__isnull=True,
            is_active=True
        ).order_by('competency__name', 'text')
        unassigned_questions = filter_by_role(unassigned_questions)

    context = {
        'department_questions': department_questions,
        'unassigned_questions': unassigned_questions,
        'departments': departments,
        'selected_department': department_id or 'all',
        'role_choices': Question.ROLE_CHOICES,
        'selected_role': selected_role or 'both',  # domyślnie 'both'
    }
    return render(request, "surveys/questions_list.html", context)



# Pytania
# --- Dodawanie pytania ---
@login_required
def question_add(request):
    if request.method == "POST":
        form = QuestionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("questions_list")
    else:
        form = QuestionForm()
    return render(request, "surveys/question_add.html", {"form": form})

# Pytania
# --- Edycja pytania ---
@login_required
def question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk)
    
    if request.method == "POST":
        # zamiast fizycznego usuwania ustawiamy is_active = False
        question.is_active = False
        question.save()
        return redirect("questions_list")
    
    return redirect("questions_list")

# Pytania
# --- Edycja pytania ---
@login_required
def question_edit(request, pk):
    question = get_object_or_404(Question, pk=pk)
    if request.method == "POST":
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            return redirect('questions_list')
    else:
        form = QuestionForm(instance=question)
    return render(request, 'surveys/question_add.html', {'form': form, 'edit': True})


# ANKIETY

@login_required
def surveys_home(request):
    surveys = Survey.objects.all()
    return render(request, "surveys/list.html", {"surveys": surveys})

@login_required
def surveys_list(request):
    surveys = Survey.objects.all().order_by('-created_at')  # najnowsze pierwsze
    return render(request, "surveys/surveys_list.html", {"surveys": surveys})

# Dodawanie ankiety
@login_required
def survey_add(request):
    if request.method == "POST":
        form = SurveyForm(request.POST)
        if form.is_valid():
            survey = form.save()
            
            # Pobranie kolejności pytań z formularza
            question_ids = request.POST.get("questions_order", "").strip().split(",")

            if not question_ids or question_ids == ['']:
                questions = Question.objects.filter(
                    Q(departments=survey.department) | Q(departments__isnull=True),
                    Q(role=survey.role) | Q(role="all"),   # <-- filtrowanie po roli
                    is_active=True
                ).distinct().order_by("id")

                for idx, q in enumerate(questions):
                    SurveyQuestion.objects.create(survey=survey, question=q, order=idx)

            else:
                for idx, qid in enumerate(question_ids):
                    if qid.strip():
                        q = get_object_or_404(
                            Question, pk=qid, is_active=True
                        )
                        SurveyQuestion.objects.create(survey=survey, question=q, order=idx)

            return redirect("surveys_list")
    else:
        form = SurveyForm()

    # Pokazujemy wszystkie pytania do HTMX lub wyboru ręcznego
    questions = Question.objects.filter(is_active=True)

    return render(request, "surveys/survey_add.html", {"form": form, "questions": questions})




# Pobieranie pytań dla wybranego działu (htmx)
def load_questions(request):
    dept_id = request.GET.get("department")
    questions = Question.objects.filter(departments__id=dept_id) if dept_id else Question.objects.none()
    return render(request, "surveys/partials/question_list.html", {"questions": questions})

def survey_edit(request, pk):
    survey = get_object_or_404(Survey, pk=pk)

    if request.method == "POST":
        form = SurveyForm(request.POST, instance=survey)

        # usuwamy pola, których nie chcemy edytować
        for field in ["department", "questions", "role"]:
            form.fields.pop(field, None)

        if form.is_valid():
            survey_obj = form.save(commit=False)
            survey_obj.role = survey.role          # zachowaj starą wartość
            survey_obj.department = survey.department  # zachowaj dział
            survey_obj.save()
            return redirect("surveys_list")
        else:
            print("❌ Błędy formularza:", form.errors)

    else:
        form = SurveyForm(instance=survey)
        for field in ["department", "questions", "role"]:
            form.fields.pop(field, None)

    return render(request, "surveys/survey_form.html", {
        "form": form,
        "title": "Edytuj ankietę"
    })

# usuwanie ankiety
@login_required
@require_POST
def survey_delete(request, pk):
    survey = get_object_or_404(Survey, pk=pk)
    survey.delete()
    return redirect('surveys_list')

@login_required
def survey_preview(request, pk):
    survey = get_object_or_404(Survey, pk=pk)
    questions = survey.surveyquestion_set.select_related('question').all()
    scale_range = range(0, 11)  # liczby od 1 do 10
    return render(request, "surveys/survey_preview.html", {
        "survey": survey,
        "questions": questions,
        "scale_range": scale_range,
    })


from .forms import SurveyFillForm

@login_required
def survey_fill(request, slug):
    survey = get_object_or_404(Survey, slug=slug)

    if not (survey.role == "both" or survey.role == request.user.role):
        return HttpResponseForbidden("Nie masz uprawnień do wypełnienia tej ankiety.")

    if SurveyResponse.objects.filter(survey=survey, user=request.user).exists():
        return render(request, "surveys/already_filled.html", {"survey": survey})

    if request.method == "POST":
        form = SurveyFillForm(survey, request.POST)
        if form.is_valid():
            response = SurveyResponse.objects.create(survey=survey, user=request.user)
            for sq in survey.surveyquestion_set.select_related("question").all():
                q = sq.question
                scale_val = form.cleaned_data.get(f"q{q.id}_scale")
                text_val = form.cleaned_data.get(f"q{q.id}_text", "")

                SurveyAnswer.objects.create(
                    response=response,
                    question=q,
                    scale_value=scale_val if scale_val else None,
                    text_value=text_val if text_val else ""
                )
            return redirect("home")
    else:
        form = SurveyFillForm(survey)

    return render(request, "surveys/survey_fill.html", {"survey": survey, "form": form})


@login_required
def survey_submit(request, slug):
    survey = get_object_or_404(Survey, slug=slug)

    # Pobierz lub utwórz odpowiedź użytkownika
    response, created = SurveyResponse.objects.get_or_create(
        survey=survey,
        user=request.user,
        defaults={'status': 'draft', 'created_at': timezone.now()}
    )

    if request.method == "POST":
        # Przechodzimy po wszystkich pytaniach ankiety
        for sq in survey.surveyquestion_set.all():
            qid = str(sq.question.id)
            value = request.POST.get(f'q{qid}', '')
            # Zaktualizuj lub stwórz odpowiedź na pytanie
            SurveyAnswer.objects.update_or_create(
                response=response,
                question=sq.question,
                defaults={'value': value}
            )
        
        # Zmień status na submitted
        response.status = 'submitted'
        response.submitted_at = timezone.now()  # jeśli masz takie pole
        response.save()

        return redirect('home')  # po wysłaniu ankiety

    # GET – wyświetlamy formularz do wypełnienia
    questions = survey.surveyquestion_set.select_related('question').all()
    scale_range = range(0, 11)
    return render(request, 'surveys/survey_fill.html', {
        'survey': survey,
        'questions': questions,
        'scale_range': scale_range
    })

@manager_or_privileged_access_required
@login_required
def survey_result(request, slug, user_id=None):
    # Pobranie ankiety
    survey = get_object_or_404(Survey, slug=slug)
      # Pobierz odpowiedź tylko tego użytkownika

    # Jeśli podano user_id (manager/admin) – pobieramy tego użytkownika
    if user_id:
        viewed_user = get_object_or_404(CustomUser, pk=user_id)
    else:
        viewed_user = request.user  # pracownik korzysta jak wcześniej

    # Pobranie odpowiedzi użytkownika
    try:
        response = SurveyResponse.objects.get(survey=survey, user=viewed_user)
    except SurveyResponse.DoesNotExist:
        response = None

    answers = SurveyAnswer.objects.filter(response=response) if response else []
    scale_range = range(0, 11)

    # Przygotowanie danych do wykresu radar
    radar_labels, radar_values = [], []
    competencies = Competency.objects.all()
    for comp in competencies:
        comp_questions = survey.questions.filter(competency=comp)
        if comp_questions.exists():
            max_total = sum([10 for q in comp_questions])
            user_total = sum([a.scale_value for a in answers if a.question in comp_questions and a.scale_value])
            percentage = round(user_total / max_total * 100, 2) if max_total > 0 else 0
            radar_labels.append(comp.name)
            radar_values.append(percentage)

    radar_data = list(zip(radar_labels, radar_values))
    show_radar = len(radar_labels) > 2

    return render(request, "surveys/survey_result.html", {
        "survey": survey,
        "answers": answers,
        "scale_range": scale_range,
        "radar_labels": radar_labels,
        "radar_values": radar_values,
        "radar_data": radar_data,
        "show_radar": show_radar,
        "viewed_user": viewed_user,  # neutralny alias
    })

@login_required
def survey_edit_response(request, slug):
    survey = get_object_or_404(Survey, slug=slug)

    if not (survey.role == "both" or survey.role == request.user.role):
        return HttpResponseForbidden("Nie masz uprawnień do edycji tej ankiety.")

    # Pobierz istniejącą odpowiedź użytkownika
    response = get_object_or_404(SurveyResponse, survey=survey, user=request.user)

    # Przygotuj initial data
    initial_data = {}
    for ans in response.answers.all():
        if ans.scale_value is not None:
            initial_data[f"q{ans.question.id}_scale"] = ans.scale_value
        if ans.text_value:
            initial_data[f"q{ans.question.id}_text"] = ans.text_value

    if request.method == "POST":
        form = SurveyFillForm(survey, request.POST)
        if form.is_valid():
            # Zapisz odpowiedzi – poprawione dla typu BOTH
            for sq in survey.surveyquestion_set.select_related("question").all():
                q = sq.question
                scale_val = form.cleaned_data.get(f"q{q.id}_scale")
                text_val = form.cleaned_data.get(f"q{q.id}_text", "")

                SurveyAnswer.objects.update_or_create(
                    response=response,
                    question=q,
                    defaults={
                        "scale_value": scale_val if scale_val else None,
                        "text_value": text_val if text_val else ""
                    }
                )
            return redirect("home")
    else:
        form = SurveyFillForm(survey, initial=initial_data)

    return render(request, "surveys/survey_fill.html", {
        "survey": survey,
        "form": form
    })

@login_required
@require_POST
def save_question_order(request, pk):
    survey = get_object_or_404(Survey, pk=pk)

    try:
        data = json.loads(request.body)
        order = data.get("order", [])  # lista ID w nowej kolejności

        for idx, sq_id in enumerate(order, start=1):
            SurveyQuestion.objects.filter(id=sq_id, survey=survey).update(order=idx)

        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


import os
import io
import base64
# Importy do wykresu radarowego (zakładam, że są na początku pliku)
import numpy as np
import matplotlib.pyplot as plt

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
# !!! DODAJ IMPORT FINDERS !!!
from django.contrib.staticfiles.finders import find 
from wkhtmltopdf.views import PDFTemplateView

from django.utils.decorators import method_decorator
@method_decorator(manager_or_privileged_access_required, name='dispatch')
class SurveyPDFView(LoginRequiredMixin, PDFTemplateView):
    template_name = "surveys/survey_pdf.html"

    cmd_options = {
        'footer-right': 'Strona [page] z [topage]',
        'footer-font-size': '8',
        'footer-spacing': '5',
        'margin-bottom': '15mm',
    }

    def get_user(self):
        user_id = self.kwargs.get("user_id")
        if user_id:
            # Użyj swojej klasy użytkownika CustomUser
            return get_object_or_404(CustomUser, pk=user_id) 
        return self.request.user

    def get_survey(self):
        slug = self.kwargs.get("slug")
        return get_object_or_404(Survey, slug=slug)

    def get_filename(self):
        survey = self.get_survey()
        user = self.get_user()
        return f"{survey.name}_{survey.year}_{user.username}.pdf"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        survey = self.get_survey()
        user = self.get_user()

        # START: POPRAWIONE POBRANIE LOGO JAKO BASE64
        logo_base64 = None
        
        # Użycie finders do zlokalizowania pliku w STATICFILES_DIRS
        logo_path = find("ats.jpg") 

        if logo_path and os.path.exists(logo_path):
            try:
                with open(logo_path, "rb") as f:
                    logo_base64 = base64.b64encode(f.read()).decode("utf-8")
            except Exception as e:
                print(f"Błąd podczas kodowania logo do base64: {e}")
                logo_base64 = None
        else:
            print("NIE ZNALEZIONO LOGO: ats_logo.png nie znaleziono w ścieżkach statycznych!")
        # KONIEC: POPRAWIONE POBRANIE LOGO JAKO BASE64

        # Pobranie odpowiedzi (niezmienione)
        try:
            # Użyj swoich modeli
            response = SurveyResponse.objects.get(survey=survey, user=user) 
            answers = SurveyAnswer.objects.filter(response=response)
        except SurveyResponse.DoesNotExist:
            answers = []

        scale_range = range(0, 11)
        # Upewnij się, że używasz właściwych klas/funkcji dla radar_labels i values
        radar_labels, radar_values = self._calculate_competency_scores(survey, answers)
        radar_image = self._generate_radar_chart(radar_labels, radar_values)
        radar_data = list(zip(radar_labels, radar_values))
        show_radar = len(radar_labels) > 2

        context.update({
            "survey": survey,
            "answers": answers,
            "scale_range": scale_range,
            "radar_image": radar_image,
            "radar_data": radar_data,
            "user": user,
            "show_radar": show_radar,
            "logo_base64": logo_base64,  # <- Zmienna dla szablonu
        })
        return context

    # Pamiętaj, że w tym miejscu muszą znajdować się też Twoje metody _calculate_competency_scores i _generate_radar_chart
    def _calculate_competency_scores(self, survey, answers):
        # ... (Twój obecny kod tej metody) ...
        labels, values = [], []
        raw_competencies = survey.questions.values_list("competency__name", flat=True).distinct()
        competencies = [c for c in raw_competencies if c and str(c).strip()]
        for comp in competencies:
            comp_questions = survey.questions.filter(competency__name=comp)
            max_total = comp_questions.count() * 10
            user_total = sum(a.scale_value for a in answers
                             if a.question in comp_questions and a.scale_value is not None)
            percentage = round(user_total / max_total * 100, 2) if max_total > 0 else 0
            labels.append(comp)
            values.append(percentage)
        return labels, values

    def _generate_radar_chart(self, labels, values):
        # ... (Twój obecny kod tej metody, wymaga importów matplotlib i numpy) ...
        if not labels or not values:
            return None
        N = len(labels)
        angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
        angles_closed = angles + [angles[0]]
        values_closed = values + [values[0]]

        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_xticks(angles)
        ax.set_xticklabels(labels)
        ax.set_ylim(0, 100)
        ax.set_rlabel_position(0)
        ax.grid(True)
        ax.set_title("WYKRES KOMPETENCJI", va='bottom', fontsize=14, fontweight='bold', pad=34)

        ax.plot(angles_closed, values_closed, linewidth=2, linestyle='solid', color='blue')
        ax.fill(angles_closed, values_closed, 'blue', alpha=0.1)

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return image_base64
    
# class SurveyPDFView(LoginRequiredMixin, TemplateView):
#     template_name = "surveys/survey_pdf.html"

#     def get_user(self):
#         user_id = self.kwargs.get("user_id")
#         if user_id:
#             return get_object_or_404(CustomUser, pk=user_id)
#         return self.request.user

#     def get_survey(self):
#         survey_id = self.kwargs.get("pk") or self.kwargs.get("survey_id")
#         return get_object_or_404(Survey, pk=survey_id)

#     def get_filename(self):
#         survey = self.get_survey()
#         user = self.get_user()
#         return f"{survey.name}_{survey.year}_{user.username}.pdf"

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         survey = self.get_survey()
#         user = self.get_user()

#         try:
#             response = SurveyResponse.objects.get(survey=survey, user=user)
#             answers = SurveyAnswer.objects.filter(response=response)
#         except SurveyResponse.DoesNotExist:
#             answers = []

#         scale_range = range(1, 11)
#         radar_labels, radar_values = self._calculate_competency_scores(survey, answers)
#         radar_data = list(zip(radar_labels, radar_values))

#         context.update({
#             "survey": survey,
#             "answers": answers,
#             "scale_range": scale_range,
#             "radar_labels": radar_labels,
#             "radar_values": radar_values,
#             "radar_data": radar_data,
#             "user": user,
#         })
#         return context

#     def _calculate_competency_scores(self, survey, answers):
#         labels = []
#         values = []

#         raw_competencies = survey.questions.values_list("competency__name", flat=True).distinct()
#         competencies = [c for c in raw_competencies if c and str(c).strip()]

#         for comp in competencies:
#             comp_questions = survey.questions.filter(competency__name=comp)
#             max_total = comp_questions.count() * 10
#             user_total = sum(
#                 a.scale_value for a in answers
#                 if a.question in comp_questions and a.scale_value is not None
#             )
#             percentage = round(user_total / max_total * 100, 2) if max_total > 0 else 0
#             labels.append(comp)
#             values.append(percentage)

#         return labels, values