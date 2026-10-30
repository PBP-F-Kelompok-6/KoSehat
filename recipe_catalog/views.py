import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST, require_GET
from .models import Recipe, EducationArticle
from .forms import RecipeForm, EducationArticleForm
from .services import get_or_fetch_recipes

def is_admin(user):
    return user.is_staff or user.is_superuser

def is_editor_or_superuser(user):
    """
    Memeriksa apakah pengguna sudah login dan merupakan admin
    atau tergabung dalam Group 'Editor'.
    """
    return user.is_authenticated and (
        is_admin(user) or user.groups.filter(name='Editor').exists()
    )

def recipe_catalog_view(request):
    recipes = get_or_fetch_recipes(number=12)
    
    editor_choice = recipes[0] if recipes else None
    display_recipes = recipes[1:7] if len(recipes) > 1 else recipes
    articles = EducationArticle.objects.all().order_by('-created_at')[:3]

    is_editor = is_editor_or_superuser(request.user)

    context = {
        'recipes': display_recipes,
        'editor_choice': editor_choice,
        'articles': articles,
        'total_recipes': len(recipes),
        'is_editor': is_editor,
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

def recipe_detail_view(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    
    context = {
        'recipe': recipe,
        'ingredients': recipe.ingredients,
        'equipments': recipe.equipments,
        'instructions': recipe.instructions,
    }
    return render(request, 'recipe_detail.html', context)

@require_GET
def recipe_detail_api(request, recipe_id):
    """
    Endpoint AJAX untuk mengembalikan data detail resep secara lengkap
    (termasuk ingredients, equipments, dan instructions) dalam format JSON.
    """
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    
    return JsonResponse({
        'status': 'success',
        'recipe': {
            'id': recipe.id,
            'title': recipe.title,
            'description': recipe.description,
            'image_url': recipe.image_url or '/static/images/placeholder-recipe.jpg',
            'prep_time_minutes': recipe.prep_time_minutes,
            'estimated_cost_formatted': recipe.estimated_cost_formatted,
            'protein_grams': recipe.protein_grams,
            'tag': recipe.tag,
            'ingredients': recipe.ingredients,
            'equipments': recipe.equipments,
            'instructions': recipe.instructions,
        }
    })

@require_GET
def article_detail_api(request, article_id):
    article = get_object_or_404(EducationArticle, pk=article_id)
    return JsonResponse({
        'status': 'success',
        'article': {
            'id': article.id,
            'title': article.title,
            'snippet': article.snippet,
            'content': article.content,
            'read_time_minutes': article.read_time_minutes,
            'category': article.category,
            'created_at': article.created_at.strftime('%d %b %Y'),
        }
    })

@login_required
@user_passes_test(is_editor_or_superuser)
@require_POST
def article_create_api(request):
    try:
        data = json.loads(request.body)
        form = EducationArticleForm(data)
    except json.JSONDecodeError:
        form = EducationArticleForm(request.POST)

    if form.is_valid():
        article = form.save()
        return JsonResponse({'status': 'success', 'message': 'Artikel berhasil dibuat', 'article_id': article.id})
    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

@login_required
@user_passes_test(is_editor_or_superuser)
@require_POST
def article_update_api(request, article_id):
    article = get_object_or_404(EducationArticle, pk=article_id)
    try:
        data = json.loads(request.body)
        form = EducationArticleForm(data, instance=article)
    except json.JSONDecodeError:
        form = EducationArticleForm(request.POST, instance=article)

    if form.is_valid():
        form.save()
        return JsonResponse({'status': 'success', 'message': 'Artikel berhasil diperbarui'})
    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

@login_required
@user_passes_test(is_editor_or_superuser)
@require_POST
def article_delete_api(request, article_id):
    article = get_object_or_404(EducationArticle, pk=article_id)
    article.delete()
    return JsonResponse({'status': 'success', 'message': 'Artikel berhasil dihapus'})