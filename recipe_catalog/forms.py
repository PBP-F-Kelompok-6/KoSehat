from django import forms
from .models import Recipe, EducationArticle

class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = [
            'title', 'description', 'image_url', 'prep_time_minutes',
            'estimated_cost', 'protein_grams', 'is_plant_based',
            'is_editor_choice', 'tag'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nama Resep'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 4}),
            'estimated_cost': forms.NumberInput(attrs={'class': 'form-input', 'step': '500'}),
        }

class EducationArticleForm(forms.ModelForm):
    class Meta:
        model = EducationArticle
        fields = ['title', 'snippet', 'content', 'read_time_minutes', 'category']