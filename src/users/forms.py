from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError

User = get_user_model()


class AdminUserUpdateForm(forms.ModelForm):
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
            "first_name":  forms.TextInput(attrs={"class": "form-control"}),
            "last_name":   forms.TextInput(attrs={"class": "form-control"}),
            "email":       forms.EmailInput(attrs={"class": "form-control"}),
            "department":  forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].required = False
        self.fields["department"].empty_label = "-"  # wybór "-" wyczyści dział

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
    password1 = forms.CharField(
        label="Hasło",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "••••••••"}),
        help_text="Min. 8 znaków, silne hasło zalecane.",
    )
    password2 = forms.CharField(
        label="Powtórz hasło",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "••••••••"}),
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "role", "department"]
        widgets = {
            "username":   forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name":  forms.TextInput(attrs={"class": "form-control"}),
            "email":      forms.EmailInput(attrs={"class": "form-control"}),
            "role":       forms.Select(attrs={"class": "form-select"}),
            "department": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].required = False
        self.fields["department"].empty_label = "-"

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise ValidationError("Login jest wymagany.")
        # dodatkowo walidacja unikalności (case-insensitive)
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Taki login już istnieje.")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Użytkownik z takim adresem e-mail już istnieje.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 != p2:
            self.add_error("password2", "Hasła nie są takie same.")
        else:
            password_validation.validate_password(p1, user=None)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["username"].strip()
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
