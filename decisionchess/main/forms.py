from django import forms
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.contrib.auth.password_validation import validate_password
from django_countries.fields import CountryField
from django.utils.html import escape, mark_safe
from .models import User

class CreateNewGameForm(forms.Form):
    main_mode_multiplayer = forms.CharField(max_length=9, label="Main Game Type", required=False, widget=forms.Select(
        choices=[('Decision', 'Decision'), ('Classical', 'Classical')], 
        attrs={'id': 'main-mode-multiplayer'}
        ))
    main_mode_computer = forms.CharField(max_length=9, label="Main Game Type", required=False, widget=forms.Select(
        choices=[('Decision', 'Decision'), ('Classical', 'Classical')], 
        attrs={'id': 'main-mode-computer'}
        ))
    main_mode_private = forms.CharField(max_length=9, label="Main Game Type", required=False, widget=forms.Select(
        choices=[('Decision', 'Decision'), ('Classical', 'Classical')], 
        attrs={'id': 'main-mode-private'}
        ))
    solo_play = forms.BooleanField(label="Solo Play", required=False, widget=forms.CheckboxInput(attrs={'id': 'solo-play-checkbox'}))
    reveal_stage_multiplayer = forms.BooleanField(label="Reveal Stage", required=False, widget=forms.CheckboxInput(attrs={'id': 'reveal-stage-multiplayer-checkbox'}))
    reveal_stage_private = forms.BooleanField(label="Reveal Stage", required=False, widget=forms.CheckboxInput(attrs={'id': 'reveal-stage-private-checkbox'}))
    decision_stage_multiplayer = forms.BooleanField(label="Decision Stage", required=False, widget=forms.CheckboxInput(attrs={'id': 'decision-stage-multiplayer-checkbox'}))
    decision_stage_private = forms.BooleanField(label="Decision Stage", required=False, widget=forms.CheckboxInput(attrs={'id': 'decision-stage-private-checkbox'}))

class ChangeThemesForm(forms.Form):
    def __init__(self, *args, **kwargs):
        themes = [
            "standard",
            "dark-wooden",
            "wooden",
            "tournament",
            "royal",
            "adversary",
            "regal",
            "portal",
            "bubblegum"
        ]
        initial_value = kwargs.pop('initial_value', 'standard')
        super(ChangeThemesForm, self).__init__(*args, **kwargs)
        for theme in themes:
            self.fields[theme] = forms.BooleanField(label=theme, required=False)
        
        theme_choices = [(theme, theme.title().replace("-", " ")) for theme in themes]
        self.fields['starting_theme'] = forms.ChoiceField(
            label='starting_theme',
            choices=theme_choices,
            widget=forms.RadioSelect(),
            initial=initial_value,
            required=True
        )

    def clean(self):
        cleaned_data = super().clean()
        selected_themes = [
            theme_name for theme_name in self.fields.keys()
            if cleaned_data.get(theme_name) and theme_name != 'starting_theme'
        ]

        if not selected_themes:
            raise ValidationError("At least one theme must be selected.")
        
        starting_theme = cleaned_data.get('starting_theme')
        if starting_theme not in selected_themes:
            raise ValidationError("Starting theme must match one of the selected themes.")
        
        return cleaned_data

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
    country = forms.CharField(max_length=200,  required=False, widget=forms.Select(choices=[('', 'None')] + list(CountryField().choices)))

    def clean_biography(self):
        biography = self.cleaned_data.get("biography")
        if biography:
            return mark_safe(escape(biography))
        return biography

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