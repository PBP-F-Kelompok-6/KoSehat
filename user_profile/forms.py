from django import forms
from django.contrib.auth.models import User
from .models import UserProfile

class UserUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False, label="Nama Depan")
    last_name = forms.CharField(max_length=30, required=False, label="Nama Belakang")
    email = forms.EmailField(required=True, label="Email UI")

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

class UserProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'health_goal',
            'activity_level',
            'daily_calorie_target',
            'daily_water_intake_target',
            'dietary_restrictions',
            'location',
            'bio',
        ]
        labels = {
            'health_goal': 'Target Utama Kesehatan',
            'activity_level': 'Tingkat Aktivitas Fisik',
            'daily_calorie_target': 'Target Kalori Harian (kcal)',
            'daily_water_intake_target': 'Target Air Minum (Liter)',
            'dietary_restrictions': 'Alergi / Preferensi Diet Spesifik',
            'location': 'Lokasi Domisili / Asrama',
            'bio': 'Bio Singkat',
        }