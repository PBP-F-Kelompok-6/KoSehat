from django import forms
from django.utils.html import strip_tags
from .models import Habit

class HabitForm(forms.ModelForm):
    class Meta:
        model = Habit
        fields = ['title', 'category', 'target_value', 'unit']

    def clean_title(self):
        title = strip_tags(self.cleaned_data.get('title', '')).strip()
        if not title:
            raise forms.ValidationError("Judul kebiasaan tidak boleh kosong atau berisi HTML murni.")
        return title

    def clean_unit(self):
        return strip_tags(self.cleaned_data.get('unit', '')).strip()