from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from surveys.models import Survey, SurveyResponse

from surveys.models import Survey, SurveyResponse

@login_required
def home(request):
    user = request.user
    surveys_list = []

    # tylko dla pracowników
    if user.role == 'employee' and user.department:
        # wszystkie ankiety dla działu użytkownika
        department_surveys = Survey.objects.filter(department=user.department)

        for survey in department_surveys:
            # sprawdź czy user już wypełnił ankietę
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
def evaluations_list(request):
    return render(request, "evaluations/list.html")  # tymczasowy szablon