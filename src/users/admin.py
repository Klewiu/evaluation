from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Department

# Rejestracja działów
admin.site.register(Department)


class CustomUserAdmin(UserAdmin):
    model = CustomUser

    # Pola wyświetlane przy edycji użytkownika
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Dane osobowe', {'fields': ('first_name', 'last_name', 'email')}),
        ('Uprawnienia', {'fields': ('role', 'department', 'is_staff', 'is_active')}),
        ('Grupy i uprawnienia', {'fields': ('groups', 'user_permissions')}),
    )

    # Pola wyświetlane przy dodawaniu nowego użytkownika
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name', 'email', 'role', 'department', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )

    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'department', 'is_staff')
    list_filter = ('role', 'department')

    # Automatyczne ustawienie is_staff dla adminów
    def save_model(self, request, obj, form, change):
        obj.is_staff = obj.role == 'admin'
        super().save_model(request, obj, form, change)

    # Uprawnienia do usuwania użytkowników
    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_superuser:
            return False
        if request.user.is_superuser or (request.user.role == 'admin' and request.user.is_staff):
            return True
        return False


admin.site.register(CustomUser, CustomUserAdmin)
