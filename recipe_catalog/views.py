import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST, require_GET
from .models import Recipe, EducationArticle, SavedRecipe
from .forms import RecipeForm, EducationArticleForm
from .services import fetch_recipes_from_api

def is_admin(user):
    return user.is_staff or user.is_superuser

def recipe_catalog_view(request):
    # Panggil Public API secara live
    api_recipes = fetch_recipes_from_api(number=12)
    
    # Pisahkan item pertama sebagai Pilihan Editor (Featured Card)
    editor_choice = api_recipes[0] if api_recipes else None
    display_recipes = api_recipes[1:7] if len(api_recipes) > 1 else api_recipes

    articles = EducationArticle.objects.all().order_by('-created_at')[:3]

    context = {
        'recipes': display_recipes,
        'editor_choice': editor_choice,
        'articles': articles,
        'total_recipes': len(api_recipes),
    }
    return render(request, 'recipe_catalog.html', context)

@require_GET
def recipe_filter_ajax(request):
    search_query = request.GET.get('q', '').strip()
    tag_filter = request.GET.get('tag', '').strip()
    max_cost = request.GET.get('max_cost', None)
    max_time = request.GET.get('max_time', None)

    # Fetch data resep langsung dari Public API secara real-time berdasarkan query pengguna
    recipes = fetch_recipes_from_api(
        query=search_query,
        tag=tag_filter,
        max_ready_time=max_time,
        max_price=max_cost,
        number=12
    )

    return JsonResponse({'status': 'success', 'recipes': recipes})

@login_required
@user_passes_test(is_admin)
def recipe_create_view(request):
    if request.method == 'POST':
        form = RecipeForm(request.POST)
        if form.is_valid():
            recipe = form.save(commit=False)
            recipe.created_by = request.user
            recipe.save()
            return JsonResponse({'status': 'success', 'message': 'Resep berhasil ditambahkan'})
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    return HttpResponseForbidden()

@login_required
@user_passes_test(is_admin)
@require_POST
def recipe_delete_view(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    recipe.delete()
    return JsonResponse({'status': 'success', 'message': 'Resep berhasil dihapus'})

@login_required
@require_POST
def toggle_save_recipe(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    saved, created = SavedRecipe.objects.get_or_dict_or_create(user=request.user, recipe=recipe) if hasattr(SavedRecipe.objects, 'get_or_dict_or_create') else SavedRecipe.objects.get_or_create(user=request.user, recipe=recipe)
    
    if not created:
        saved.delete()
        return JsonResponse({'status': 'unbookmarked'})
    return JsonResponse({'status': 'bookmarked'})