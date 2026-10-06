from django import forms
from .models import Gig, WorkPhase, GigEquipment, Client, CustomInvoiceItem, InvoiceSnapshot

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

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'ico', 'email', 'phone', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Název firmy nebo jméno'}),
            'ico': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'IČO klienta'}),
            'email': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telefon'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Interní poznámky...'}),
        }

class CustomInvoiceItemForm(forms.ModelForm):
    class Meta:
        model = CustomInvoiceItem
        fields = ['item_type', 'description', 'fixed_price', 'quantity', 'unit_price']
        widgets = {
            'item_type': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Popis (např. "Cesta + palivo")'}),
            'fixed_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '500'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'placeholder': 'Počet hodin'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': 'Cena za hodinu'}),
        }
        labels = {
            'item_type': 'Typ položky',
            'description': 'Popis',
            'fixed_price': 'Cena (Kč)',
            'quantity': 'Počet hodin',
            'unit_price': 'Cena za hodinu (Kč/h)',
        }

class InvoicePaymentForm(forms.Form):
    payment_method = forms.ChoiceField(
        choices=InvoiceSnapshot.PAYMENT_METHOD_CHOICES,
        label='Stav úhrady',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    payment_date = forms.DateField(
        required=False,
        label='Datum úhrady',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    due_date = forms.DateField(
        required=False,
        label='Datum splatnosti',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        payment_date = cleaned_data.get('payment_date')
        due_date = cleaned_data.get('due_date')

        if payment_method != 'unpaid' and not payment_date:
            self.add_error('payment_date', 'U uhrazené faktury vyplňte datum úhrady.')
        elif payment_method == 'unpaid' and payment_date:
            self.add_error('payment_date', 'Datum úhrady lze vyplnit pouze u uhrazené faktury.')

        if payment_method == 'unpaid' and not due_date:
            self.add_error('due_date', 'U nezaplacené faktury vyplňte datum splatnosti.')
        elif payment_method != 'unpaid':
            cleaned_data['due_date'] = None

        return cleaned_data