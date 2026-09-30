from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction

from clients.models import DeliveryAgent
from market.models import categories, product


class ProductForm(forms.ModelForm):
    class Meta:
        model = product
        fields = (
            'name',
            'price',
            'category',
            'description',
            'image',
            'stock',
            'is_active',
            'is_hot_deal',
            'hot_deal_rank',
            'hot_deal_label',
        )
        widgets = {'description': forms.Textarea(attrs={'rows': 4})}


class CategoryForm(forms.ModelForm):
    class Meta:
        model = categories
        fields = ('name', 'description')
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class AgentCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20)
    vehicle_number = forms.CharField(max_length=30, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    @transaction.atomic
    def save(self, created_by, commit=True):
        user = super().save(commit=False)
        user.is_staff = False
        if commit:
            user.save()
            DeliveryAgent.objects.create(
                user=user,
                phone=self.cleaned_data['phone'],
                vehicle_number=self.cleaned_data['vehicle_number'],
                created_by=created_by,
            )
        return user
