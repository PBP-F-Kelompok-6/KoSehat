from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", lambda request: redirect("user_profile:login"), name="home_redirect"),
    path("", include("app.dashboard_analytics.urls", namespace="dashboard_analytics")),
    path("auth/", include("user_profile.urls")),
    path("habit-tracker/", include("habit_tracker.urls")),
    path("meal-planner/", include("meal_planner.urls")),
    path("catalog/", include("recipe_catalog.urls")),
]
