import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST, require_GET
from .models import Recipe, EducationArticle, SavedRecipe
from .forms import RecipeForm, EducationArticleForm

def is_admin(user):
    return user.is_staff or user.is_superuser

def recipe_catalog_view(request):
    recipes = Recipe.objects.all().order_by('-created_at')
    editor_choice = Recipe.objects.filter(is_editor_choice=True).first()
    articles = EducationArticle.objects.all().order_by('-created_at')[:3]
    
    saved_recipe_ids = []
    if request.user.is_authenticated:
        saved_recipe_ids = list(SavedRecipe.objects.filter(user=request.user).values_list('recipe_id', flat=True))

    context = {
        'recipes': recipes,
        'editor_choice': editor_choice,
        'articles': articles,
        'saved_recipe_ids': saved_recipe_ids,
        'is_admin': is_admin(request.user) if request.user.is_authenticated else False,
    }
    return render(request, 'recipe_catalog.html', context)

@require_GET
def recipe_filter_ajax(request):
    search_query = request.GET.get('q', '').strip()
    tag_filter = request.GET.get('tag', '').strip()
    max_cost = request.GET.get('max_cost', None)
    max_time = request.GET.get('max_time', None)

    recipes = Recipe.objects.all()

    if search_query:
        recipes = recipes.filter(title__icontains=search_query)
    if tag_filter and tag_filter != 'Semua':
        if tag_filter == 'Plant-based':
            recipes = recipes.filter(is_plant_based=True)
        else:
            recipes = recipes.filter(tag=tag_filter)
    if max_cost:
        recipes = recipes.filter(estimated_cost__lte=float(max_cost))
    if max_time:
        recipes = recipes.filter(prep_time_minutes__lte=int(max_time))

    data = [
        {
            'id': r.id,
            'title': r.title,
            'description': r.description,
            'image_url': r.image_url or 'https://via.placeholder.com/300x200',
            'prep_time_minutes': r.prep_time_minutes,
            'estimated_cost': f"Rp{r.estimated_cost:,.0f}".replace(',', '.'),
            'protein_grams': r.protein_grams,
            'tag': r.tag,
        }
        for r in recipes
    ]
    return JsonResponse({'status': 'success', 'recipes': data})

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