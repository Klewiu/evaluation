# users/forms.py
from django import forms
from django.contrib.auth import get_user_model, password_validation
from .models import Department  # ← added

User = get_user_model()


class AdminUserUpdateForm(forms.ModelForm):
    email = forms.EmailField(
        label="E-mail",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "inputmode": "email",
            "autocomplete": "email",
        }),
        error_messages={
            "invalid": "Błędny format e-mail",
        },
        required=False,
    )

    password1 = forms.CharField(
        label="Nowe hasło",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "••••••••"}),
        required=False,
        help_text="Pozostaw puste, aby nie zmieniać."
    )
    password2 = forms.CharField(
        label="Powtórz hasło",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "••••••••"}),
        required=False,
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "department"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name":  forms.TextInput(attrs={"class": "form-control"}),
            "department": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].required = False
        self.fields["department"].empty_label = "-"

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "Hasła nie są takie same.")
            else:
                password_validation.validate_password(p1, user=self.instance)
        return cleaned


class AdminUserCreateForm(forms.ModelForm):
    email = forms.EmailField(
        label="E-mail",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "inputmode": "email",
            "autocomplete": "email",
        }),
        error_messages={
            "invalid": "Błędny format e-mail",
        },
    )

    password1 = forms.CharField(
        label="Hasło",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "••••••••"}),
    )
    password2 = forms.CharField(
        label="Powtórz hasło",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "••••••••"}),
    )

    class Meta:
        model = User
        fields = ["username", "role", "first_name", "last_name", "email", "department"]
        widgets = {
            "username":   forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "role":       forms.Select(attrs={"class": "form-select"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name":  forms.TextInput(attrs={"class": "form-control"}),
            "department": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].required = False
        self.fields["department"].empty_label = "-"

    def clean(self):
        cleaned = super().clean()

        username = cleaned.get("username", "").strip()
        if username and User.objects.filter(username__iexact=username).exists():
            self.add_error("username", "Ten login jest już zajęty.")

        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "Hasła nie są takie same.")
            else:
                dummy = User(username=username or None)
                password_validation.validate_password(p1, user=dummy)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        p1 = self.cleaned_data.get("password1")
        if p1:
            user.set_password(p1)
        if commit:
            user.save()
        return user


# ======================================================
# DEPARTMENT FORM
# ======================================================
class DepartmentForm(forms.ModelForm):
    name = forms.CharField(
        label="Nazwa działu",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "np. Księgowość, IT, Marketing",
            "autocomplete": "off",
        }),
        error_messages={
            "required": "Nazwa działu jest wymagana.",
        },
    )

    class Meta:
        model = Department
        fields = ["name"]

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if Department.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Taki dział już istnieje.")
        return name
