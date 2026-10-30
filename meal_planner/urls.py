from django.urls import path

from . import views

app_name = 'meal_planner'

urlpatterns = [
    path('', views.planner, name='index'),
    path('tambah/', views.meal_create, name='meal_create'),
    path('hitung-kalori/', views.estimate_calories, name='estimate_calories'),
    path('<int:pk>/ubah/', views.meal_update, name='meal_update'),
    path('<int:pk>/hapus/', views.meal_delete, name='meal_delete'),
]