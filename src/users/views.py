# users/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.contrib import messages
import json

# ---- for departments ----
from django.db.models import Count, OuterRef, Subquery, IntegerField
from .models import Department
from .forms import AdminUserUpdateForm, AdminUserCreateForm, DepartmentForm
# -------------------------

User = get_user_model()


def is_admin_or_superuser(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, "role", "") == "admin")


@login_required
def home(request):
    return render(request, 'evaluations/home.html', {'user': request.user})


@login_required
@user_passes_test(is_admin_or_superuser)
def users_list(request):
    users = User.objects.all().order_by("username")
    return render(request, "users/list.html", {"users": users})


# -------------------- CREATE --------------------
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
        # Re-render modal with field errors
        return render(request, "users/_create_form.html", {"form": form})

    user = form.save()
    messages.success(request, "Użytkownik utworzony.")

    users = User.objects.all().order_by("username")
    resp = render(request, "users/_tbody_oob.html", {"users": users})
    resp["HX-Trigger"] = json.dumps({"userCreated": True})
    return resp
# ------------------ /CREATE --------------------


# --------------------- EDIT --------------------
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
    resp["HX-Trigger"] = json.dumps({"userUpdated": True})
    return resp
# ------------------- /EDIT ---------------------


# ------------------- TOGGLE ACTIVE -------------
@login_required
@user_passes_test(is_admin_or_superuser)
@require_POST
def user_toggle_active(request, pk):
    user_obj = get_object_or_404(User, pk=pk)

    if user_obj.pk == request.user.pk:
        return HttpResponse("Nie możesz zablokować własnego konta.", status=400)

    user_obj.is_active = not user_obj.is_active
    user_obj.save(update_fields=["is_active"])

    messages.success(
        request,
        "Użytkownik odblokowany." if user_obj.is_active else "Użytkownik zablokowany."
    )

    return render(request, "users/_row_oob.html", {"u": user_obj})
# ----------------- /TOGGLE ACTIVE --------------


# --------------------- DELETE ------------------
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
# ------------------- /DELETE -------------------


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


# ======================================================
# DEPARTMENTS
# ======================================================

@login_required
@user_passes_test(is_admin_or_superuser)
def departments_list(request):
    """
    Lists departments with user counts via subquery (robust to any related_name).
    """
    count_qs = (
        User.objects
        .filter(department=OuterRef("pk"))
        .values("department")
        .annotate(c=Count("*"))
        .values("c")
    )
    departments = (
        Department.objects
        .all()
        .annotate(user_count=Subquery(count_qs, output_field=IntegerField()))
        .order_by("name")
    )
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

    d = form.save()
    messages.success(request, "Dział utworzony.")

    resp = render(request, "departments/_row_oob_append.html", {"d": d})
    # Fire after-settle so OOB swaps/backdrop state are finalized, then close specific modal:
    payload = {"deptCreated": {"target": "#createDepartmentModal"}}
    resp["HX-Trigger"] = json.dumps(payload)
    resp["HX-Trigger-After-Settle"] = json.dumps(payload)
    return resp
# ---------- /CREATE ----------


# ---------- EDIT ----------
@login_required
@user_passes_test(is_admin_or_superuser)
def department_edit(request, pk):
    d = get_object_or_404(Department, pk=pk)
    form = DepartmentForm(instance=d)
    return render(request, "departments/_edit_form.html", {"form": form, "dept": d})


@login_required
@user_passes_test(is_admin_or_superuser)
@require_POST
def department_update(request, pk):
    d = get_object_or_404(Department, pk=pk)
    form = DepartmentForm(request.POST, instance=d)
    if not form.is_valid():
        return render(request, "departments/_edit_form.html", {"form": form, "dept": d})

    d = form.save()
    messages.success(request, "Dział zaktualizowany.")

    resp = render(request, "departments/_row_oob.html", {"d": d})
    payload = {"deptUpdated": {"target": "#editDepartmentModal"}}
    resp["HX-Trigger"] = json.dumps(payload)
    resp["HX-Trigger-After-Settle"] = json.dumps(payload)
    return resp
# ---------- /EDIT ----------


# ---------- DELETE ----------
@login_required
@user_passes_test(is_admin_or_superuser)
def department_confirm_delete(request, pk):
    d = get_object_or_404(Department, pk=pk)
    user_count = User.objects.filter(department=d).count()
    return render(request, "departments/_confirm_delete.html", {"dept": d, "user_count": user_count})


@login_required
@user_passes_test(is_admin_or_superuser)
@require_POST
def department_delete(request, pk):
    d = get_object_or_404(Department, pk=pk)
    row_id = f"department-row-{d.pk}"
    name = d.name
    d.delete()

    messages.success(
        request,
        f"Dział „{name}” został usunięty. Użytkownicy przypisani do niego otrzymali status BRAK DZIAŁU."
    )

    resp = render(request, "departments/_row_oob_delete.html", {"row_id": row_id})
    payload = {"deptDeleted": {"target": "#confirmDeleteDepartmentModal"}}
    resp["HX-Trigger"] = json.dumps(payload)
    resp["HX-Trigger-After-Settle"] = json.dumps(payload)
    return resp
# ---------- /DELETE ----------
