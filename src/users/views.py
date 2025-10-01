# users/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.contrib import messages
import json

from .forms import AdminUserUpdateForm, AdminUserCreateForm

User = get_user_model()


# Access helper: only admin role or superuser
def is_admin_or_superuser(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, "role", "") == "admin")


# Home (unchanged)
@login_required
def home(request):
    return render(request, 'evaluations/home.html', {'user': request.user})


# List all users (admin/superuser only)
@login_required
@user_passes_test(is_admin_or_superuser)
def users_list(request):
    users = User.objects.all().order_by("username")
    return render(request, "users/list.html", {"users": users})


# ---------- CREATE ----------
@login_required
@user_passes_test(is_admin_or_superuser)
def user_new(request):
    form = AdminUserCreateForm()
    return render(request, "users/_create_form.html", {"form": form})


@login_required
@user_passes_test(is_admin_or_superuser)
@require_POST
def user_create(request):
    form = AdminUserCreateForm(request.POST)
    if not form.is_valid():
        # 200 => stay in modal and show field errors
        return render(request, "users/_create_form.html", {"form": form})

    user = form.save()
    messages.success(request, "Użytkownik utworzony.")

    # Append new row OOB and fire event AFTER swap/settle to close modal via base.html
    resp = render(request, "users/_row_oob_append.html", {"u": user})
    resp["HX-Trigger-After-Settle"] = "userCreated"
    return resp
# ---------- /CREATE ----------


# ---------- EDIT ----------
@login_required
@user_passes_test(is_admin_or_superuser)
def user_edit(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    form = AdminUserUpdateForm(instance=user_obj)  # pre-filled
    return render(request, "users/_edit_form.html", {"form": form, "user_obj": user_obj})


@login_required
@user_passes_test(is_admin_or_superuser)
@require_POST
def user_update(request, pk):
    user_obj = get_object_or_404(User, pk=pk)

    form = AdminUserUpdateForm(request.POST, instance=user_obj)
    if not form.is_valid():
        # 200 => swap modal content with form + errors
        return render(request, "users/_edit_form.html", {"form": form, "user_obj": user_obj})

    user = form.save(commit=False)
    pwd1 = form.cleaned_data.get("password1")
    if pwd1:
        user.set_password(pwd1)
    user.save()

    messages.success(request, "Użytkownik zaktualizowany.")

    # Replace row OOB and fire event AFTER swap/settle to close modal via base.html
    resp = render(request, "users/_row_oob.html", {"u": user})
    resp["HX-Trigger-After-Settle"] = "userUpdated"
    return resp
# ---------- /EDIT ----------


# ---------- DELETE ----------
@login_required
@user_passes_test(is_admin_or_superuser)
def user_confirm_delete(request, pk):
    user_obj = get_object_or_404(User, pk=pk)

    # Only a superuser may delete another superuser
    if user_obj.is_superuser and not request.user.is_superuser:
        return HttpResponse("Nie masz uprawnień do usunięcia superużytkownika.", status=403)

    return render(request, "users/_confirm_delete.html", {"user_obj": user_obj})


@login_required
@user_passes_test(is_admin_or_superuser)
@require_POST
def user_delete(request, pk):
    user_obj = get_object_or_404(User, pk=pk)

    if user_obj.pk == request.user.pk:
        messages.error(request, "Nie możesz usunąć sam siebie.")
        return HttpResponse("Nie możesz usunąć samego siebie.", status=400)

    if user_obj.is_superuser and not request.user.is_superuser:
        messages.error(request, "Nie masz uprawnień do usunięcia superużytkownika.")
        return HttpResponse("Brak uprawnień.", status=403)

    user_obj.delete()
    messages.success(request, "Użytkownik usunięty.")
    return HttpResponse("")
# ---------- /DELETE ----------


# Live username availability check (HTMX GET)
@login_required
@user_passes_test(is_admin_or_superuser)
def check_username(request):
    raw = request.GET.get("username") or request.GET.get("q") or ""
    username = raw.strip()
    taken = User.objects.filter(username__iexact=username).exists() if username else False

    if not username:
        html = ""
    elif taken:
        html = "<small class='text-danger'>Ten login jest już zajęty.</small>"
    else:
        html = "<small class='text-success'>Login dostępny.</small>"

    return HttpResponse(html)
