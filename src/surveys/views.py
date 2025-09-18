from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from users.models import Department
from .models import Question, Competency
from .forms import QuestionForm, CompetencyForm


@login_required
def surveys_list(request):
    return render(request, "surveys/list.html")

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