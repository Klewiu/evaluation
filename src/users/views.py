from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db.models import Count
import json

from .forms import AdminUserUpdateForm, AdminUserCreateForm, DepartmentForm
from .models import Department

User = get_user_model()


# ======================================================
# HELPERS
# ======================================================

def is_admin_or_superuser(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, "role", "") == "admin")


# ======================================================
# HOME
# ======================================================

@login_required
def home(request):
    return render(request, 'evaluations/home.html', {'user': request.user})


# ======================================================
# USERS
# ======================================================

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
        return render(request, "users/_create_form.html", {"form": form})

    user = form.save()
    messages.success(request, "Użytkownik utworzony.")

    resp = render(request, "users/_row_oob_append.html", {"u": user})
    resp["HX-Trigger"] = json.dumps({"userCreated": {"target": "#createUserModal"}})
    return resp
# ---------- /CREATE ----------


# ---------- EDIT ----------
@login_required
@user_passes_test(is_admin_or_superuser)
def user_edit(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    form = AdminUserUpdateForm(instance=user_obj)
    return render(request, "users/_edit_form.html", {"form": form, "user_obj": user_obj})


@login_required
@user_passes_test(is_admin_or_superuser)
@require_POST
def user_update(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    form = AdminUserUpdateForm(request.POST, instance=user_obj)
    if not form.is_valid():
        return render(request, "users/_edit_form.html", {"form": form, "user_obj": user_obj})

    user = form.save(commit=False)
    pwd1 = form.cleaned_data.get("password1")
    if pwd1:
        user.set_password(pwd1)
    user.save()

    messages.success(request, "Użytkownik zaktualizowany.")

    resp = render(request, "users/_row_oob.html", {"u": user})
    resp["HX-Trigger"] = json.dumps({"userUpdated": {"target": "#editUserModal"}})
    return resp
# ---------- /EDIT ----------


# ---------- TOGGLE ACTIVE (BLOCK / UNBLOCK) ----------
@login_required
@user_passes_test(is_admin_or_superuser)
@require_POST
def user_toggle_active(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    user_obj.is_active = not user_obj.is_active
    user_obj.save()

    status = "zablokowany" if not user_obj.is_active else "aktywny"
    messages.success(request, f"Użytkownik {user_obj.username} jest teraz {status}.")

    resp = render(request, "users/_row_oob.html", {"u": user_obj})
    resp["HX-Trigger"] = json.dumps({"userUpdated": {"target": "#user-table-body"}})
    return resp
# ---------- /TOGGLE ACTIVE ----------


# ---------- DELETE ----------
@login_required
@user_passes_test(is_admin_or_superuser)
def user_confirm_delete(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
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


# ---------- CHECK USERNAME ----------
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
# ---------- /CHECK USERNAME ----------


# ======================================================
# DEPARTMENTS (DZIAŁY)
# ======================================================

@login_required
@user_passes_test(is_admin_or_superuser)
def departments_list(request):
    related_name = User._meta.model_name
    departments = Department.objects.annotate(user_count=Count(related_name)).order_by("name")
    return render(request, "departments/list.html", {"departments": departments})


# ---------- CREATE ----------
@login_required
@user_passes_test(is_admin_or_superuser)
def department_new(request):
    form = DepartmentForm()
    return render(request, "departments/_create_form.html", {"form": form})


@login_required
@user_passes_test(is_admin_or_superuser)
@require_POST
def department_create(request):
    form = DepartmentForm(request.POST)
    if not form.is_valid():
        return render(request, "departments/_create_form.html", {"form": form})

    dept = form.save()
    messages.success(request, "Dział utworzony.")
    resp = render(request, "departments/_row_oob_append.html", {"d": dept})
    resp["HX-Trigger"] = json.dumps({"deptCreated": {"target": "#createDepartmentModal"}})
    return resp
# ---------- /CREATE ----------


# ---------- EDIT ----------
@login_required
@user_passes_test(is_admin_or_superuser)
def department_edit(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    form = DepartmentForm(instance=dept)
    return render(request, "departments/_edit_form.html", {"form": form, "dept": dept})


@login_required
@user_passes_test(is_admin_or_superuser)
@require_POST
def department_update(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    form = DepartmentForm(request.POST, instance=dept)
    if not form.is_valid():
        return render(request, "departments/_edit_form.html", {"form": form, "dept": dept})

    dept = form.save()
    messages.success(request, "Dział zaktualizowany.")
    resp = render(request, "departments/_row_oob.html", {"d": dept})
    resp["HX-Trigger"] = json.dumps({"deptUpdated": {"target": "#editDepartmentModal"}})
    return resp
# ---------- /EDIT ----------


# ---------- DELETE ----------
@login_required
@user_passes_test(is_admin_or_superuser)
def department_confirm_delete(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    related_name = User._meta.model_name
    user_count = (
        Department.objects.filter(pk=dept.pk)
        .annotate(user_count=Count(related_name))
        .first()
        .user_count
        if Department.objects.filter(pk=dept.pk).exists()
        else 0
    )
    return render(request, "departments/_confirm_delete.html", {"dept": dept, "user_count": user_count})


@login_required
@user_passes_test(is_admin_or_superuser)
@require_POST
def department_delete(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    name = dept.name
    dept.delete()
    messages.success(request, f"Dział „{name}” został usunięty. Użytkownicy przypisani do niego otrzymali status BRAK DZIAŁU.")
    return HttpResponse("")
# ---------- /DELETE ----------
