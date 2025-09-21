from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from django.utils import timezone

from users.models import Department
from .models import Question, Competency, Survey, SurveyQuestion, SurveyResponse, SurveyAnswer
from .forms import QuestionForm, CompetencyForm, SurveyForm 


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
@login_required
def questions_list(request):
    department_id = request.GET.get('department_id')
    departments = Department.objects.all()
    
    if department_id and department_id != 'all':
        filtered_department = Department.objects.get(id=department_id)
        department_questions = {
            filtered_department: Question.objects.filter(departments=filtered_department)
        }
        unassigned_questions = Question.objects.filter(departments__isnull=True)
    else:
        # wszystkie pytania pogrupowane po działach
        department_questions = {}
        for dept in departments:
            dept_questions = Question.objects.filter(departments=dept)
            if dept_questions.exists():
                department_questions[dept] = dept_questions
        unassigned_questions = Question.objects.filter(departments__isnull=True)

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
        question.delete()
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
    surveys = Survey.objects.all()
    return render(request, "surveys/surveys_list.html", {"surveys": surveys})

# Dodanie ankiety
@login_required
def survey_add(request):
    if request.method == "POST":
        form = SurveyForm(request.POST)
        if form.is_valid():
            survey = form.save()
            
            # Pobranie kolejności pytań z formularza
            question_ids = request.POST.get("questions_order", "").split(",")
            
            if question_ids == [''] or not question_ids:
                # Jeśli brak zaznaczonych pytań, dodaj wszystkie z działu ankiety
                questions = Question.objects.filter(departments=survey.department)
                for idx, q in enumerate(questions):
                    SurveyQuestion.objects.create(survey=survey, question=q, order=idx)
            else:
                # Dodaj pytania wybrane przez użytkownika
                for idx, qid in enumerate(question_ids):
                    if qid.strip():
                        q = Question.objects.get(pk=qid)
                        SurveyQuestion.objects.create(survey=survey, question=q, order=idx)

            return redirect("surveys_list")
    else:
        form = SurveyForm()

    # Pobranie wszystkich pytań do wyświetlenia w formularzu (opcjonalnie)
    questions = Question.objects.all()

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
    scale_range = range(1, 10)  # liczby od 1 do 10
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
    scale_range = range(1, 10)

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
    scale_range = range(1, 10)
    return render(request, 'surveys/survey_fill.html', {
        'survey': survey,
        'questions': questions,
        'scale_range': scale_range
    })

@login_required
def survey_result(request, pk):
    survey = get_object_or_404(Survey, pk=pk)

    # Pobieramy odpowiedź zalogowanego użytkownika dla tej ankiety
    try:
        response = SurveyResponse.objects.get(survey=survey, user=request.user)
    except SurveyResponse.DoesNotExist:
        response = None

    answers = SurveyAnswer.objects.filter(response=response) if response else []

    scale_range = range(1, 10)  # dla pytań typu scale

    return render(request, "surveys/survey_result.html", {
        "survey": survey,
        "answers": answers,
        "scale_range": scale_range,
    })