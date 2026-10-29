from django import forms
from django.utils.html import strip_tags
from .models import Habit, EnergyLog

class HabitForm(forms.ModelForm):
    class Meta:
        model = Habit
        fields = ['title', 'category', 'target_value', 'unit']

    def clean_title(self):
        title = strip_tags(self.cleaned_data.get('title', '')).strip()
        if not title:
            raise forms.ValidationError("Judul kebiasaan tidak boleh kosong.")
        return title

    def clean_unit(self):
        return strip_tags(self.cleaned_data.get('unit', '')).strip()

class EnergyLogForm(forms.ModelForm):
    class Meta:
        model = EnergyLog
        fields = ['energy_level', 'focus_minutes']

    def clean_energy_level(self):
        level = self.cleaned_data.get('energy_level')
        if level < 1 or level > 10:
            raise forms.ValidationError("Tingkat energi harus berada di skala 1 - 10.")
        return level

    def clean_focus_minutes(self):
        minutes = self.cleaned_data.get('focus_minutes')
        if minutes < 0:
            raise forms.ValidationError("Waktu fokus tidak boleh bernilai negatif.")
        return minutes

class AddFocusTimeForm(forms.Form):
    additional_minutes = forms.IntegerField(
        min_value=1,
        error_messages={'min_value': 'Durasi fokus minimal 1 menit.'}
    )