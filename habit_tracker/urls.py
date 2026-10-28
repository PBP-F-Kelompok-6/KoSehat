from django.urls import path
from . import views

app_name = 'habit_tracker'

urlpatterns = [
    path('', views.habit_tracker_view, name='index'),
    path('api/habits/', views.get_habits_json, name='get_habits'),
    path('api/add/', views.add_habit_ajax, name='add_habit'),
    path('api/toggle/<int:habit_id>/', views.toggle_habit_ajax, name='toggle_habit'),
    path('api/delete/<int:habit_id>/', views.delete_habit_ajax, name='delete_habit'),
]