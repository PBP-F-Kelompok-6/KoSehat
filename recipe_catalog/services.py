import requests
from django.conf import settings
from .models import Recipe

SPOONACULAR_API_KEY = getattr(settings, 'SPOONACULAR_API_KEY', 'DUMMY_KEY')

def fetch_and_seed_recipes():
    url = f"https://api.spoonacular.com/recipes/complexSearch?apiKey={SPOONACULAR_API_KEY}&addRecipeInformation=true&number=50"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json().get('results', [])
            for item in data:
                Recipe.objects.get_or_create(
                    external_api_id=item.get('id'),
                    defaults={
                        'title': item.get('title'),
                        'description': item.get('summary', '')[:300],
                        'image_url': item.get('image'),
                        'prep_time_minutes': item.get('readyInMinutes', 15),
                        'estimated_cost': 15000.00,
                        'protein_grams': 15,
                        'is_plant_based': item.get('vegetarian', False),
                        'tag': 'Plant-based' if item.get('vegetarian') else 'Cepat',
                    }
                )
            return True
    except Exception:
        pass
    return False