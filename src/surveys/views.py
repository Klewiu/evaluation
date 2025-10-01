import json
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

# KOMPETENCJE

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
    departments = Department.objects.all().order_by('name')  # alfabetyczna kolejność działów

    if department_id and department_id != 'all':
        # Wybrany konkretny dział
        filtered_department = get_object_or_404(Department, id=department_id)
        department_questions = OrderedDict()

        dept_questions = Question.objects.filter(
            departments=filtered_department,
            is_active=True
        ).order_by('competency__name', 'text')  # sortowanie po kompetencjach i tekście

        if dept_questions.exists():
            department_questions[filtered_department] = dept_questions

        # Pytania niezwiązane z żadnym działem
        unassigned_questions = Question.objects.filter(
            departments__isnull=True,
            is_active=True
        ).order_by('competency__name', 'text')

    else:
        # Wszystkie pytania pogrupowane po działach
        department_questions = OrderedDict()
        for dept in departments:
            dept_questions = Question.objects.filter(
                departments=dept,
                is_active=True
            ).order_by('competency__name', 'text')
            if dept_questions.exists():
                department_questions[dept] = dept_questions

        # Pytania niezwiązane z żadnym działem
        unassigned_questions = Question.objects.filter(
            departments__isnull=True,
            is_active=True
        ).order_by('competency__name', 'text')

    context = {
        'department_questions': department_questions,
        'unassigned_questions': unassigned_questions,
        'departments': departments,
        'selected_department': department_id or 'all',
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

# Dodanie ankiety
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
                    is_active=True
                ).distinct().order_by("id")
    
                for idx, q in enumerate(questions):
                    SurveyQuestion.objects.create(survey=survey, question=q, order=idx)

            else:
                # Dodaj pytania wybrane przez użytkownika, tylko jeśli są aktywne
                for idx, qid in enumerate(question_ids):
                    if qid.strip():
                        q = get_object_or_404(Question, pk=qid, is_active=True)
                        SurveyQuestion.objects.create(survey=survey, question=q, order=idx)

            return redirect("surveys_list")
    else:
        form = SurveyForm()

    # Pobranie wszystkich aktywnych pytań do wyświetlenia w formularzu
    questions = Question.objects.filter(is_active=True)

    return render(request, "surveys/survey_add.html", {"form": form, "questions": questions})



# Pobieranie pytań dla wybranego działu (htmx)
def load_questions(request):
    dept_id = request.GET.get("department")
    questions = Question.objects.filter(departments__id=dept_id) if dept_id else Question.objects.none()
    return render(request, "surveys/partials/question_list.html", {"questions": questions})

# edytowanie ankiety
def survey_edit(request, pk):
    survey = get_object_or_404(Survey, pk=pk)
    if request.method == "POST":
        form = SurveyForm(request.POST, instance=survey)
        if form.is_valid():
            form.save()
            return redirect("surveys_list")
    else:
        form = SurveyForm(instance=survey)
    return render(request, "surveys/survey_form.html", {"form": form, "title": "Edytuj ankietę"})

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
    scale_range = range(1, 11)  # liczby od 1 do 10
    return render(request, "surveys/survey_preview.html", {
        "survey": survey,
        "questions": questions,
        "scale_range": scale_range,
    })


@login_required
def survey_fill(request, pk):
    survey = get_object_or_404(Survey, pk=pk)

    # tylko pracownik może wypełniać
    if request.user.role != "employee":
        return HttpResponseForbidden("Tylko pracownicy mogą wypełniać ankiety.")

    # sprawdź czy user już wypełnił
    if SurveyResponse.objects.filter(survey=survey, user=request.user).exists():
        return render(request, "surveys/already_filled.html", {"survey": survey})

    if request.method == "POST":
        # utwórz odpowiedź zbiorczą
        response = SurveyResponse.objects.create(survey=survey, user=request.user)

        # przeiteruj pytania i zapisz odpowiedzi
        for sq in survey.surveyquestion_set.select_related("question").all():
            q = sq.question
            scale_val = request.POST.get(f"q{q.id}_scale")
            text_val = request.POST.get(f"q{q.id}_text")

            SurveyAnswer.objects.create(
                response=response,
                question=q,
                scale_value=scale_val if scale_val else None,
                text_value=text_val if text_val else ""
            )

        return redirect("home")  # po wypełnieniu wróć na dashboard

    questions = survey.surveyquestion_set.select_related("question").all()
    scale_range = range(1, 11)

    return render(request, "surveys/survey_fill.html", {
        "survey": survey,
        "questions": questions,
        "scale_range": scale_range,
    })


@login_required
def survey_submit(request, pk):
    survey = get_object_or_404(Survey, pk=pk)

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
    scale_range = range(1, 11)
    return render(request, 'surveys/survey_fill.html', {
        'survey': survey,
        'questions': questions,
        'scale_range': scale_range
    })


@login_required
def survey_result(request, pk):
    survey = get_object_or_404(Survey, pk=pk)

    try:
        response = SurveyResponse.objects.get(survey=survey, user=request.user)
    except SurveyResponse.DoesNotExist:
        response = None

    answers = SurveyAnswer.objects.filter(response=response) if response else []
    scale_range = range(1, 11)  # dla pytań typu scale

    # Przygotowanie danych do wykresu radar
    radar_labels = []
    radar_values = []

    competencies = Competency.objects.all()
    for comp in competencies:
        comp_questions = survey.questions.filter(competency=comp)
        if comp_questions.exists():
            max_total = sum([10 for q in comp_questions])  # maksymalna suma skali pytań
            user_total = sum([a.scale_value for a in answers if a.question in comp_questions and a.scale_value])
            percentage = round(user_total / max_total * 100, 2) if max_total > 0 else 0
            radar_labels.append(comp.name)
            radar_values.append(percentage)

    # Przygotowanie danych do tabeli jako lista krotek
    radar_data = list(zip(radar_labels, radar_values))

    # Flaga decydująca o wyświetleniu wykresu
    show_radar = len(radar_labels) > 2

    return render(request, "surveys/survey_result.html", {
        "survey": survey,
        "answers": answers,
        "scale_range": scale_range,
        "radar_labels": radar_labels,
        "radar_values": radar_values,
        "radar_data": radar_data,  # <-- teraz przekazujemy dane do tabeli
        "show_radar": show_radar,
    })

@login_required
def survey_edit_response(request, pk):
    survey = get_object_or_404(Survey, pk=pk)

    if request.user.role != "employee":
        return HttpResponseForbidden("Tylko pracownicy mogą edytować swoje odpowiedzi.")

    # Pobierz istniejącą odpowiedź
    response = get_object_or_404(SurveyResponse, survey=survey, user=request.user)
    questions = survey.surveyquestion_set.select_related("question").all()

    # Tworzymy słownik: {question.id: SurveyAnswer}
    answers = {a.question.id: a for a in response.answers.all()}

    if request.method == "POST":
        for sq in questions:
            q = sq.question
            scale_val = request.POST.get(f"q{q.id}_scale")
            text_val = request.POST.get(f"q{q.id}_text")

            SurveyAnswer.objects.update_or_create(
                response=response,
                question=q,
                defaults={
                    "scale_value": scale_val if scale_val else None,
                    "text_value": text_val if text_val else "",
                },
            )

        return redirect("home")

    return render(request, "surveys/survey_edit_response.html", {
        "survey": survey,
        "questions": questions,
        "answers": answers,
        "scale_range": range(1, 11),
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

class SurveyPDFView(LoginRequiredMixin, PDFTemplateView):
    template_name = "surveys/survey_pdf.html"

    def get_filename(self):
        survey = get_object_or_404(Survey, pk=self.kwargs["pk"])
        return f"{survey.name}_{survey.year}_{self.request.user.username}.pdf"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        survey = get_object_or_404(Survey, pk=self.kwargs["pk"])

        # Pobranie odpowiedzi użytkownika
        try:
            response = SurveyResponse.objects.get(survey=survey, user=self.request.user)
            answers = SurveyAnswer.objects.filter(response=response)
        except SurveyResponse.DoesNotExist:
            answers = []

        scale_range = range(1, 11)
        radar_labels, radar_values = self._calculate_competency_scores(survey, answers)
        radar_image = self._generate_radar_chart(radar_labels, radar_values)

        # Tworzymy dane do tabeli pod wykresem
        radar_data = list(zip(radar_labels, radar_values))

        context.update({
            "survey": survey,
            "answers": answers,
            "scale_range": scale_range,
            "radar_image": radar_image,
            "radar_data": radar_data,
        })
        return context

    def _calculate_competency_scores(self, survey, answers):
        labels = []
        values = []

        # Pobranie unikalnych kompetencji i odfiltrowanie pustych
        raw_competencies = survey.questions.values_list("competency__name", flat=True).distinct()
        competencies = [c for c in raw_competencies if c and str(c).strip()]

        for comp in competencies:
            comp_questions = survey.questions.filter(competency__name=comp)
            max_total = comp_questions.count() * 10
            user_total = sum(
                a.scale_value for a in answers
                if a.question in comp_questions and a.scale_value is not None
            )
            percentage = round(user_total / max_total * 100, 2) if max_total > 0 else 0
            labels.append(comp)
            values.append(percentage)

        return labels, values

    def _generate_radar_chart(self, labels, values):
        if not labels or not values:
            return None

        N = len(labels)
        angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
        angles_closed = angles + [angles[0]]
        values_closed = values + [values[0]]

        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))

        # Estetyka wykresu
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_xticks(angles)
        ax.set_xticklabels(labels)
        ax.set_ylim(0, 100)
        ax.set_rlabel_position(0)
        ax.grid(True)
        ax.set_title("Wykres kompetencji", va='bottom')

        # Linie promieniowe dla podziału koła
        for angle in angles:
            ax.plot([angle, angle], [0, 100], color='gray', linewidth=0.5, linestyle='dashed')

        # Rysowanie danych
        ax.plot(angles_closed, values_closed, linewidth=2, linestyle='solid', color='blue')
        ax.fill(angles_closed, values_closed, 'blue', alpha=0.1)

        # Konwersja do base64
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)

        return image_base64