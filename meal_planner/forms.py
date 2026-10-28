from django import forms

from .models import Meal


class MealForm(forms.ModelForm):
    class Meta:
        model = Meal
        fields = [
            'date', 'meal_type', 'name', 'estimated_cost', 'calories',
            'is_homemade', 'packaging_used', 'notes',
        ]
        labels = {
            'date': 'Tanggal',
            'meal_type': 'Waktu makan',
            'name': 'Menu',
            'estimated_cost': 'Perkiraan biaya (Rp)',
            'calories': 'Kalori (kkal)',
            'is_homemade': 'Masak sendiri (bukan cepat saji)',
            'packaging_used': 'Kemasan sekali pakai yang dipakai',
            'notes': 'Catatan',
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'name': forms.TextInput(attrs={'placeholder': 'mis. Nasi telur + tumis kangkung'}),
            'packaging_used': forms.NumberInput(attrs={'min': 0}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }