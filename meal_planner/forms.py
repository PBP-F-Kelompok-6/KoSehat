from django import forms

from .models import Meal


class MealForm(forms.ModelForm):
    class Meta:
        model = Meal
        fields = [
            'date', 'meal_type', 'name', 'estimated_cost', 'calories',
            'is_homemade', 'packaging_avoided', 'notes',
        ]
        labels = {
            'date': 'Tanggal',
            'meal_type': 'Waktu makan',
            'name': 'Menu',
            'estimated_cost': 'Perkiraan biaya (Rp)',
            'calories': 'Kalori (kkal)',
            'is_homemade': 'Masak sendiri (bukan cepat saji)',
            'packaging_avoided': 'Kemasan sekali pakai yang dihindari',
            'notes': 'Catatan',
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'name': forms.TextInput(attrs={'placeholder': 'mis. Nasi telur + tumis kangkung'}),
            'packaging_avoided': forms.NumberInput(attrs={'min': 0}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }