from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile

class UserRegisterForm(UserCreationForm):
    """Form untuk pendaftaran akun lokal baru."""
    email = forms.EmailField(required=True, help_text="Wajib diisi dengan email aktif.")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

class UserUpdateForm(forms.ModelForm):
    """Form untuk memperbarui informasi dasar pengguna."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

class UserProfileUpdateForm(forms.ModelForm):
    """Form untuk memperbarui target dan preferensi kesehatan."""
    class Meta:
        model = UserProfile
        fields = [
            'health_goal', 
            'activity_level', 
            'daily_calorie_target', 
            'daily_water_intake_target', 
            'dietary_restrictions', 
            'location', 
            'bio'
        ]
        labels = {
            'health_goal': 'Target Utama Kesehatan',
            'activity_level': 'Tingkat Aktivitas Fisik',
            'daily_calorie_target': 'Target Kalori Harian (kcal)',
            'daily_water_intake_target': 'Target Konsumsi Air (Liter)',
            'dietary_restrictions': 'Alergi atau Preferensi Diet',
            'location': 'Lokasi Tempat Tinggal (Kos / Rumah / Asrama)',
            'bio': 'Bio Singkat',
        }
        widgets = {
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contoh: Kos Bu Nanik, Kukusan, atau Asrama UI'
            }),
            'dietary_restrictions': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contoh: Vegetarian, Tanpa Kacang, dll.'
            }),
        }