
from django.shortcuts import render

def landing_page(request):
    return render(request, "recipe_catalog.html")

def dashboard(request):
    return render(request, "dashboard.html")

def impact_analytics(request):
    return render(request, "impact_analytics.html")
