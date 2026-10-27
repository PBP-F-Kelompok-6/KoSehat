from django.urls import path

from . import views

app_name = 'meal_planner'

urlpatterns = [
    path('', views.planner, name='index'),
    path('tambah/', views.meal_create, name='meal_create'),
    path('<int:pk>/hapus/', views.meal_delete, name='meal_delete'),
]
