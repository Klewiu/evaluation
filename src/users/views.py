from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def home(request):
    return render(request, 'evaluations/home.html', {'user': request.user})

@login_required
def users_list(request):
    return render(request, "users/list.html")  # tymczasowy szablon