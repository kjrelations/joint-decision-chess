from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.core.exceptions import ObjectDoesNotExist
from main.models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit

class RegisterForm(UserCreationForm):
    email = forms.EmailField()
    agree_to_terms = forms.BooleanField(
        required=True,
        initial=False,
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2", "agree_to_terms"]

    def clean_username(self):
        username = self.cleaned_data['username']
        if self.username.startswith("Anon-") or self.username.lower() == "anonymous":
            raise forms.ValidationError("Usernames starting with 'Anon' are not allowed.")
        return username

class ResendActivationEmailForm(forms.Form):
    email = forms.EmailField(label='Email Address')

    # TODO Consider whether this init is necessary
    def __init__(self, *args, **kwargs):
        super(ResendActivationEmailForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'email',
            Submit('submit', 'Resend Activation Email')
        )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        try:
            user = User.objects.get(email=email)
            if user.is_active:
                raise forms.ValidationError('This account is already active')
        except ObjectDoesNotExist:
            raise forms.ValidationError('No user with this email address found')

        return email
    
class CustomResetForm(forms.Form):
    email = forms.EmailField(label='Email')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        try:
            _ = User.objects.get(email=email)
        except ObjectDoesNotExist:
            raise forms.ValidationError('No user with this email address found')

        return email
    
class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('old_password')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["new_password1"])
        if commit:
            user.save()
        return user