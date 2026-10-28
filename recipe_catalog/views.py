import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST, require_GET
from .models import Recipe, EducationArticle, SavedRecipe
from .forms import RecipeForm, EducationArticleForm
from .services import get_or_fetch_recipes

def is_admin(user):
    return user.is_staff or user.is_superuser

def recipe_catalog_view(request):
    recipes = get_or_fetch_recipes(number=12)
    
    editor_choice = recipes[0] if recipes else None
    display_recipes = recipes[1:7] if len(recipes) > 1 else recipes
    articles = EducationArticle.objects.all().order_by('-created_at')[:3]

    context = {
        'recipes': display_recipes,
        'editor_choice': editor_choice,
        'articles': articles,
        'total_recipes': len(recipes),
    }
    return render(request, 'recipe_catalog.html', context)

@require_GET
def recipe_filter_ajax(request):
    search_query = request.GET.get('q', '').strip()
    tag_filter = request.GET.get('tag', '').strip()
    max_cost = request.GET.get('max_cost', None)
    max_time = request.GET.get('max_time', None)

    recipes = get_or_fetch_recipes(
        query=search_query,
        tag=tag_filter,
        max_ready_time=max_time,
        max_price=max_cost,
        number=12
    )
    
    recipes_data = [
        {
            'id': r.id,
            'external_api_id': r.external_api_id,
            'title': r.title,
            'description': r.description,
            'image_url': r.image_url,
            'prep_time_minutes': r.prep_time_minutes,
            'estimated_cost': float(r.estimated_cost),
            'estimated_cost_formatted': f"Rp{r.estimated_cost:,.0f}".replace(',', '.'),
            'protein_grams': r.protein_grams,
            'tag': r.tag,
        }
        for r in recipes
    ]

    return JsonResponse({'status': 'success', 'recipes': recipes_data})

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
    saved, created = SavedRecipe.objects.get_or_create(user=request.user, recipe=recipe)
    
    if not created:
        saved.delete()
        return JsonResponse({'status': 'unbookmarked'})
    return JsonResponse({'status': 'bookmarked'})

def recipe_detail_view(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    
    context = {
        'recipe': recipe,
        'ingredients': recipe.ingredients,
        'equipments': recipe.equipments,
        'instructions': recipe.instructions,
    }
    return render(request, 'recipe_detail.html', context)