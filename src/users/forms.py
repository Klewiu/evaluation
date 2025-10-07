# users/forms.py
from django import forms
from django.contrib.auth import get_user_model, password_validation

User = get_user_model()


class AdminUserUpdateForm(forms.ModelForm):
    # Override email field to use Polish 'invalid' message (and disable native browser validation via TextInput)
    email = forms.EmailField(
        label="E-mail",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "inputmode": "email",
            "autocomplete": "email",
        }),
        error_messages={
            "invalid": "Błędny format e-mail",
            # "required": "Adres e-mail jest wymagany.",  # odkomentuj jeśli chcesz
        },
        required=False,  # jak u Ciebie – e-mail opcjonalny przy edycji
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
            # "email": set above
            "department": forms.Select(attrs={"class": "form-select"}),
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
    # Email with Polish 'invalid' message (again TextInput to avoid native browser message)
    email = forms.EmailField(
        label="E-mail",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "inputmode": "email",
            "autocomplete": "email",
        }),
        error_messages={
            "invalid": "Błędny format e-mail",
            # "required": "Adres e-mail jest wymagany.",  # odkomentuj jeśli chcesz
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
            # "email": set above
            "department": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].required = False
        self.fields["department"].empty_label = "-"  # "-" = brak działu

    def clean(self):
        cleaned = super().clean()

        # Unique username (case-insensitive)
        username = cleaned.get("username", "").strip()
        if username and User.objects.filter(username__iexact=username).exists():
            self.add_error("username", "Ten login jest już zajęty.")

        # Passwords match + strength
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "Hasła nie są takie same.")
            else:
                # validate strength against a new (unsaved) user instance
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
