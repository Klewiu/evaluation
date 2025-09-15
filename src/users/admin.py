from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from .models import CustomUser, Department

admin.site.register(Department)

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'department')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('role', 'department')}),
    )

    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'department', 'is_staff')
    list_filter = ('role', 'department')

    def save_model(self, request, obj, form, change):
        if obj.role == 'admin':
            obj.is_staff = True
        else:
            obj.is_staff = False
        super().save_model(request, obj, form, change)

     # Uprawnienia do usuwania użytkowników
    def has_delete_permission(self, request, obj=None):
        # Nigdy nie pozwalamy usuwać superusera
        if obj and obj.is_superuser:
            return False
        # Superuser i administratorzy mogą usuwać innych użytkowników
        if request.user.is_superuser or (request.user.role == 'admin' and request.user.is_staff):
            return True
        return False


admin.site.register(CustomUser, CustomUserAdmin)
