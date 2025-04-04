from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email'})
    )
    phone_no = forms.CharField(
        label=_("Phone Number (Optional)"),
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'autocomplete': 'tel'})
    )

    class Meta:
        model = User
        fields = ("username", "email", "phone_no", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Tailwind classes to form fields
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'py-3 px-4 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-[#3E8061] focus:border-[#3E8061] sm:text-sm'
            })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError(_("A user with that email already exists."))
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError(_("A user with that username already exists."))
        return username
    
