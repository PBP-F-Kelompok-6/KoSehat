from django import forms
from django.utils.html import strip_tags

from .models import EnergyLog, Habit


class HabitForm(forms.ModelForm):
    class Meta:
        model = Habit
        fields = ["title", "category", "target_value", "unit"]

    def clean_title(self):
        title = strip_tags(
            self.cleaned_data.get("title", "")
        ).strip()

        if not title:
            raise forms.ValidationError(
                "Judul kebiasaan tidak boleh kosong."
            )

        return title

    def clean_unit(self):
        unit = strip_tags(
            self.cleaned_data.get("unit", "")
        ).strip()

        if not unit:
            raise forms.ValidationError(
                "Satuan kebiasaan tidak boleh kosong."
            )

        return unit


class EnergyLogForm(forms.ModelForm):
    class Meta:
        model = EnergyLog
        fields = ["focus_minutes"]


class AddFocusTimeForm(forms.Form):
    additional_minutes = forms.IntegerField(
        min_value=1,
        error_messages={
            "min_value": "Durasi fokus minimal 1 menit.",
        },
    )


class AddHabitProgressForm(forms.Form):
    additional_value = forms.IntegerField(
        min_value=1,
        error_messages={
            "min_value": "Progress harus lebih dari 0.",
        },
    )


class SleepSettingForm(forms.Form):
    target_hours = forms.FloatField(
        min_value=1.0,
        max_value=24.0,
    )
    sleep_hours = forms.IntegerField(
        min_value=0,
        max_value=23,
    )
    sleep_minutes = forms.IntegerField(
        min_value=0,
        max_value=59,
    )


class HydrationForm(forms.Form):
    amount_ml = forms.IntegerField(
        min_value=1,
        error_messages={
            "min_value": "Jumlah hidrasi minimal 1 ml.",
        },
    )
