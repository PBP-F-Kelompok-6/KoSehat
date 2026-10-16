from django.db import models
from django.contrib.auth.models import User

class Recipe(models.Model):
    CATEGORY_CHOICES = [
        ('Hemat', 'Hemat'),
        ('Minim alat', 'Minim alat'),
        ('Plant-based', 'Plant-based'),
        ('Sarapan', 'Sarapan'),
        ('Cepat', 'Cepat'),
        ('Lokal', 'Lokal'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    image_url = models.URLField(max_length=500, blank=True, null=True)
    prep_time_minutes = models.PositiveIntegerField(default=15)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, default=15000.00)
    protein_grams = models.PositiveIntegerField(default=0)
    is_plant_based = models.BooleanField(default=False)
    is_editor_choice = models.BooleanField(default=False)
    tag = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Hemat')
    external_api_id = models.IntegerField(blank=True, null=True, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class EducationArticle(models.Model):
    title = models.CharField(max_length=255)
    snippet = models.CharField(max_length=300)
    content = models.TextField()
    read_time_minutes = models.PositiveIntegerField(default=5)
    category = models.CharField(max_length=50, default='Nutrisi')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class SavedRecipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_query_name='saved_recipes')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'recipe')