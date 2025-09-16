from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def surveys_list(request):
    return render(request, "surveys/list.html")  # <- ścieżka musi zgadzać się z folderem