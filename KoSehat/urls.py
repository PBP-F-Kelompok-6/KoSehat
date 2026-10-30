from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('user_profile:login'), name='home_redirect'),
    path('auth/', include('user_profile.urls')),
    path('meal-planner/', include('meal_planner.urls')),
]