from django import forms
from django.contrib.auth.forms import UserCreationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit
from django.core.exceptions import ObjectDoesNotExist
from main.models import User

class RegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

class ResendActivationEmailForm(forms.Form):
    email = forms.EmailField(label='Email Address')

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
    
