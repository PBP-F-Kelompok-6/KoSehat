from django.urls import path
from . import views

app_name = 'recipe_catalog'

urlpatterns = [
    path('', views.recipe_catalog_view, name='katalog'),
    path('<int:recipe_id>/', views.recipe_detail_view, name='recipe_detail'),
    path('api/filter/', views.recipe_filter_ajax, name='filter_ajax'),
    path('add/', views.recipe_create_view, name='add_recipe'),
    path('delete/<int:recipe_id>/', views.recipe_delete_view, name='delete_recipe'),
    path('bookmark/<int:recipe_id>/', views.toggle_save_recipe, name='toggle_bookmark'),
]