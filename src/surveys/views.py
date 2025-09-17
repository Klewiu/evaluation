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
# --- Wyświetlanie listy kompetencji pogrupowanych według działów ---
@login_required
def competencies_list(request):
    # Pobieramy wszystkie działy
    departments = Department.objects.all()

    # Tworzymy słownik dział -> lista kompetencji
    department_competencies = {}
    for department in departments:
        comps = Competency.objects.filter(departments=department)
        if comps.exists():
            department_competencies[department] = comps

    # Pobieramy kompetencje nieprzypisane do żadnego działu
    unassigned = Competency.objects.filter(departments__isnull=True)

    context = {
        "department_competencies": department_competencies,
        "unassigned_competencies": unassigned
    }
    return render(request, "surveys/competencies_list.html", context)

# Kompetencje
# --- Dodawanie, edycja, usuwanie kompetencji ---
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

# Kompetencje
# --- Edycja kompetencji ---
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

    return render(request, "surveys/competency_edit.html", {"form": form, "competency": competency})

# Kompetencje
# --- Usuwanie kompetencji ---
@require_POST
def competency_delete(request, pk):
    competency = get_object_or_404(Competency, pk=pk)
    scope = request.POST.get('scope')

    if scope == 'all':
        # Usuwamy całą kompetencję
        competency.delete()
    else:
        # Usuwamy tylko przypisanie do wybranego działu
        department_id = request.POST.get('department_id')
        if department_id:
            department = get_object_or_404(Department, pk=department_id)
            competency.departments.remove(department)
        # Jeśli kompetencja nie ma już żadnych działów, możesz opcjonalnie zostawić ją jako "bez działu"

    return redirect('competencies_list')

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