from django.urls import path

from . import views

app_name = 'meal_planner'

urlpatterns = [
    path('', views.planner, name='index'),
]
