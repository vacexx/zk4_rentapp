from django import forms
from .models import Gig, WorkPhase, GigEquipment

class GigForm(forms.ModelForm):
    class Meta:
        model = Gig
        fields = ['name', 'date', 'client', 'status', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'client': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class WorkPhaseForm(forms.ModelForm):
    class Meta:
        model = WorkPhase
        fields = ['phase', 'start_time', 'end_time', 'hourly_rate']
        widgets = {
            'phase': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'hourly_rate': forms.Select(attrs={'class': 'form-select'}),
        }

class GigEquipmentForm(forms.ModelForm):
    class Meta:
        model = GigEquipment
        fields = ['equipment', 'quantity']
        widgets = {
            'equipment': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }
        labels = {
            'equipment': 'Vybavení',
            'quantity': 'Počet dní',
        }