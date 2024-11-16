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
        choices=[('Decision', 'Decision'), ('Classical', 'Classical')], # TODO Rename to Decision Chess and Chess later with 'Decision' and 'Traditional' values
        attrs={'id': 'main-mode-private'}
        ))
    timed_mode_multiplayer = forms.CharField(max_length=9, label="Timed Subvariant", required=False, widget=forms.Select(
        choices=[('', 'None'), ('Classical', 'Classical'), ('Rapid', 'Rapid'), ('Blitz', 'Blitz')], 
        attrs={'id': 'timed-mode-multiplayer'}
        ))
    timed_mode_private = forms.CharField(max_length=9, label="Standard Subvariants", required=False, widget=forms.Select(
        choices=[('', ''), ('Classical', 'Classical'), ('Rapid', 'Rapid'), ('Blitz', 'Blitz')], 
        attrs={'id': 'timed-mode-private'}
        ))
    increment_multiplayer = forms.CharField(max_length=9, label="Increment", required=False, widget=forms.Select(
        choices=[('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('10', '10')], 
        attrs={'id': 'increment-multiplayer'}
        ))
    increment_private = forms.CharField(max_length=9, label="Increment", required=False, widget=forms.Select(
        choices=[('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('10', '10')], 
        attrs={'id': 'increment-private'}
        ))
    solo_play = forms.BooleanField(label="Solo Play", required=False, widget=forms.CheckboxInput(attrs={'id': 'solo-play-checkbox'}))
    reveal_stage_multiplayer = forms.BooleanField(label="Reveal Stage", required=False, widget=forms.CheckboxInput(attrs={'id': 'reveal-stage-multiplayer-checkbox'}))
    reveal_stage_private = forms.BooleanField(label="Reveal Stage", required=False, widget=forms.CheckboxInput(attrs={'id': 'reveal-stage-private-checkbox'}))
    decision_stage_multiplayer = forms.BooleanField(label="Decision Stage", required=False, widget=forms.CheckboxInput(attrs={'id': 'decision-stage-multiplayer-checkbox'}))
    decision_stage_private = forms.BooleanField(label="Decision Stage", required=False, widget=forms.CheckboxInput(attrs={'id': 'decision-stage-private-checkbox'}))
    suggestive_multiplayer = forms.BooleanField(label="Suggestive Variant", required=False, widget=forms.CheckboxInput(attrs={'id': 'suggestive-multiplayer-checkbox'}))
    suggestive_private = forms.BooleanField(label="Suggestive Variant", required=False, widget=forms.CheckboxInput(attrs={'id': 'suggestive-private-checkbox'}))

class BoardEditorForm(forms.Form):
    white_kingside_castle = forms.BooleanField(label="O-O", required=False, widget=forms.CheckboxInput(attrs={'id': 'white-kingside-castle'}))
    white_queenside_castle = forms.BooleanField(label="O-O-O", required=False, widget=forms.CheckboxInput(attrs={'id': 'white-queenside-castle'}))
    black_kingside_castle = forms.BooleanField(label="O-O", required=False, widget=forms.CheckboxInput(attrs={'id': 'black-kingside-castle'}))
    black_queenside_castle = forms.BooleanField(label="O-O-O", required=False, widget=forms.CheckboxInput(attrs={'id': 'black-queenside-castle'}))
    match_type = forms.ChoiceField(
        choices=[('multiplayer', 'Multiplayer Game'), ('computer', 'Computer Game'), ('solo', 'Solo Game')],
        widget=forms.RadioSelect,
        label="Match Type",
        required=True
    )

class GameSearch(forms.Form):
    player_1 = forms.CharField(
        max_length=150,
        label="Player 1",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter a username'
        })
    )
    player_2 = forms.CharField(
        max_length=150,
        label="Player 2",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter a username'
        })
    )
    white = forms.CharField(max_length=150, label="White", required=False, widget=forms.Select(
        choices=[('', '')], 
        attrs={'id': 'white-player'}
    ))
    black = forms.CharField(max_length=150, label="Black", required=False, widget=forms.Select(
        choices=[('', '')], 
        attrs={'id': 'black-player'}
    ))
    outcome = forms.CharField(max_length=10, label="Outcome", required=False, widget=forms.Select(
        choices=[('', ''), ('1-0', '1-0'), ('0-1', '0-1'), ('1-0 or 0-1', '1-0 or 0-1'), ('1-1', '1-1'), ('½-½', '½-½'),], 
        attrs={'id': 'outcome'}
    ))
    winning_player = forms.CharField(max_length=150, label="Winner", required=False, widget=forms.Select(
        choices=[('', '')], 
        attrs={'id': 'winner'}
    ))
    losing_player = forms.CharField(max_length=150, label="Loser", required=False, widget=forms.Select(
        choices=[('', '')], 
        attrs={'id': 'loser'}
    ))
    game_type = forms.CharField(max_length=150, label="Game Type", required=False, widget=forms.Select(
        choices=[('', ''), ('Standard', 'Standard'), ('Complete', 'Complete'), ('Relay', 'Relay'), ('Countdown', 'Countdown')], 
        attrs={'id': 'game-type'}
    ))
    start_date = forms.DateField(
        label="Start Date",
        required=False,
        widget=forms.DateInput(attrs={
            "type": "date",
            "placeholder": "YYYY-MM-DD"
        })
    )

    def clean_white(self):
        white = self.cleaned_data.get('white')
        
        if white and white != '' and \
           (white != self.cleaned_data.get('player_1') and white != self.cleaned_data.get('player_2')):
            raise ValidationError("Invalid white player selected.")
        
        return white
    
    def clean_black(self):
        black = self.cleaned_data.get('black')
        
        if black and black != '' and \
           (black != self.cleaned_data.get('player_1') and black != self.cleaned_data.get('player_2')):
            raise ValidationError("Invalid black player selected.")
        
        return black
    
    def clean_winning_player(self):
        winning_player = self.cleaned_data.get('winning_player')
        
        if winning_player and winning_player != '' and \
           (winning_player != self.cleaned_data.get('player_1') and winning_player != self.cleaned_data.get('player_2')):
            raise ValidationError("Invalid white player selected.")
        
        return winning_player
    
    def clean_losing_player(self):
        losing_player = self.cleaned_data.get('losing_player')
        
        if losing_player and losing_player != '' and \
           (losing_player != self.cleaned_data.get('player_1') and losing_player != self.cleaned_data.get('player_2')):
            raise ValidationError("Invalid black player selected.")
        
        return losing_player

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