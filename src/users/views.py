from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.contrib.auth import get_user_model

# helper to restrict access
def is_admin_or_superuser(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, "role", "") == "admin")

# home view (still here!)
@login_required
def home(request):
    return render(request, 'evaluations/home.html', {'user': request.user})

# list all users (only superuser + admin role)
@login_required
@user_passes_test(is_admin_or_superuser)
def users_list(request):
    User = get_user_model()
    users = User.objects.all().order_by("username")
    return render(request, "users/list.html", {"users": users})

# load confirmation modal content
@login_required
@user_passes_test(is_admin_or_superuser)
def user_confirm_delete(request, pk):
    User = get_user_model()
    user_obj = get_object_or_404(User, pk=pk)

    # prevent deleting superusers unless current user is superuser
    if user_obj.is_superuser and not request.user.is_superuser:
        return HttpResponse("Nie masz uprawnień do usunięcia superużytkownika.", status=403)

    return render(request, "users/_confirm_delete.html", {"user_obj": user_obj})

# handle deletion request
@login_required
@user_passes_test(is_admin_or_superuser)
@require_POST
def user_delete(request, pk):
    User = get_user_model()
    user_obj = get_object_or_404(User, pk=pk)

    if user_obj.pk == request.user.pk:
        return HttpResponse("Nie możesz usunąć samego siebie.", status=400)
    if user_obj.is_superuser and not request.user.is_superuser:
        return HttpResponse("Nie masz uprawnień do usunięcia superużytkownika.", status=403)

    user_obj.delete()

    return HttpResponse("")  