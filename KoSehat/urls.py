from django.contrib import admin
from django.urls import include, path
from django.shortcuts import redirect

from KoSehat.views import landing_page

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', lambda request: redirect('user_profile:login'), name='home_redirect'),
    path('auth/', include('user_profile.urls')),
    path('meal-planner/', include('meal_planner.urls')),
    path('catalog/', include('recipe_catalog.urls')),
    path("habit-tracker/", include("habit_tracker.urls")),
]