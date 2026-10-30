from django.contrib import admin
from django.urls import include, path

from KoSehat.views import landing_page

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing_page, name='landing_page'),
    path("auth/", include("user_profile.urls")),
    path("meal-planner/", include("meal_planner.urls")),
    path("habit-tracker/", include("habit_tracker.urls")),
]