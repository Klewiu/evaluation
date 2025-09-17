from django import forms
from django.contrib.auth import get_user_model, password_validation

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
        # Let ModelForm pre-fill with instance values (no clearing).
        # Only configure the department select to allow "-" which maps to None.
        self.fields["department"].required = False
        self.fields["department"].empty_label = "-"  # choosing "-" will clear department

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
