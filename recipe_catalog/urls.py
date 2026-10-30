from django.urls import path
from . import views

app_name = 'recipe_catalog'

urlpatterns = [
    path('', views.recipe_catalog_view, name='catalog'),
    path('api/filter/', views.recipe_filter_ajax, name='filter_ajax'),
    path('<int:recipe_id>/', views.recipe_detail_view, name='recipe_detail'),
    path('api/detail/<int:recipe_id>/', views.recipe_detail_api, name='recipe_detail_api'),
    path('add/', views.recipe_create_view, name='add_recipe'),
    path('delete/<int:recipe_id>/', views.recipe_delete_view, name='delete_recipe'),
    path('bookmark/<int:recipe_id>/', views.toggle_save_recipe, name='toggle_bookmark'),
    path('api/article/<int:article_id>/', views.article_detail_api, name='article_detail_api'),
    path('api/article/create/', views.article_create_api, name='article_create_api'),
    path('api/article/update/<int:article_id>/', views.article_update_api, name='article_update_api'),
    path('api/article/delete/<int:article_id>/', views.article_delete_api, name='article_delete_api'),
]