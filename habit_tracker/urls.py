from django.urls import path
from . import views

app_name = 'habit_tracker'

urlpatterns = [
    path('', views.habit_tracker_view, name='index'),
    path('api/habits/', views.get_habits_json, name='get_habits'),
    path('api/add/', views.add_habit_ajax, name='add_habit'),
    path('api/toggle/<int:habit_id>/', views.toggle_habit_ajax, name='toggle_habit'),
    path('api/delete/<int:habit_id>/', views.delete_habit_ajax, name='delete_habit'),
    path('api/energy/', views.log_energy_ajax, name='log_energy'),
    path('api/focus/add/', views.add_focus_time_ajax, name='add_focus_time'),
    path('api/sleep/settings/', views.log_sleep_settings_ajax, name='log_sleep_settings'),
]