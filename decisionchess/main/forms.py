from django import forms
from django.core.exceptions import ObjectDoesNotExist
from .models import User

class ChangeEmailForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput)
    email = forms.EmailField(label='New Email Address')

    def __init__(self, user, *args, **kwargs):
        super(ChangeEmailForm, self).__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not self.user.check_password(password):
            raise forms.ValidationError('Incorrect password')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        try:
            user = User.objects.get(email=email)
            if user is not None:
                raise forms.ValidationError('This email already exists')
        except ObjectDoesNotExist:
            return email