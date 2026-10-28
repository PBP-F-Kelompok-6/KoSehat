from django.urls import path
import django_cas_ng.views as cas_views
from . import views

urlpatterns = [
    path('login/', cas_views.LoginView.as_view(), name='cas_ng_login'),
    path('logout/', cas_views.LogoutView.as_view(), name='cas_ng_logout'),
    path('profile/', views.profile_view, name='profile'),
]