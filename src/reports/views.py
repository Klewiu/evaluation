from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from users.models import Department, CustomUser

@login_required
def reports_home(request):
    departments = Department.objects.all().order_by('name')
    employees = CustomUser.objects.filter(is_active=True).order_by('last_name', 'first_name')

    context = {
        'departments': departments,
        'employees': employees,
    }
    return render(request, 'reports/reports_home.html', context)
