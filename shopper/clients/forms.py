from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from market.models import categories

from .models import Profile


class CustomerRegistrationForm(UserCreationForm):
    email = forms.EmailField()
    contact = forms.CharField(max_length=20, label='Phone number')
    priority_categories = forms.ModelMultipleChoiceField(
        queryset=categories.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Shopping priorities',
        help_text='Choose categories you care about so hot deals can appear first for you.',
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile = Profile.objects.create(user=user, contact=self.cleaned_data['contact'])
            profile.priority_categories.set(self.cleaned_data['priority_categories'])
        return user


class CheckoutForm(forms.Form):
    PAYMENT_CHOICES = [
        ('cash', 'Cash on delivery'),
        ('mobile', 'Mobile money'),
        ('card', 'Card payment'),
    ]

    full_name = forms.CharField(max_length=150)
    phone = forms.CharField(max_length=20)
    address = forms.CharField(widget=forms.Textarea)
    payment_method = forms.ChoiceField(choices=PAYMENT_CHOICES)
