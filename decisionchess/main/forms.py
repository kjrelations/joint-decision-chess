from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.password_validation import validate_password
from django_countries.fields import CountryField
from .models import User

class ChangeEmailForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput)
    email = forms.EmailField(label='New Email Address')

    def __init__(self, user, *args, **kwargs):
        super(ChangeEmailForm, self).__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        password = self.cleaned_data.get('password')

        try:
            validate_password(password, user=self.user)
        except forms.ValidationError as error:
            raise forms.ValidationError(error)

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

class EditProfile(forms.Form):
    biography = forms.CharField(widget=forms.Textarea(attrs={'rows': 8}), required=False)
    country = CountryField(blank=True, blank_label="None").formfield()

class CloseAccount(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        super(CloseAccount, self).__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        password = self.cleaned_data.get('password')

        try:
            validate_password(password, user=self.user)
        except forms.ValidationError as error:
            raise forms.ValidationError(error)

        if not self.user.check_password(password):
            raise forms.ValidationError('Incorrect password')