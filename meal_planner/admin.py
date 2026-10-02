from django.contrib import admin

from .models import Meal


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ('date', 'meal_type', 'name', 'estimated_cost', 'is_homemade', 'packaging_avoided', 'user')
    list_filter = ('meal_type', 'is_homemade', 'date')
    search_fields = ('name',)
