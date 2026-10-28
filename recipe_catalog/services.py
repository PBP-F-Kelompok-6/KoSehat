import requests
from django.conf import settings

SPOONACULAR_API_KEY = getattr(settings, 'SPOONACULAR_API_KEY', '')
BASE_URL = 'https://api.spoonacular.com/recipes/complexSearch'

def fetch_recipes_from_api(query='', tag='', max_ready_time=None, max_price=None, number=12):
    params = {
        'apiKey': SPOONACULAR_API_KEY,
        'addRecipeInformation': 'true',
        'addRecipeNutrition': 'true',
        'addRecipeInstructions': 'true',
        'fillIngredients': 'true',
        'number': number,
    }

    if query:
        params['query'] = query

    if tag == 'Plant-based':
        params['diet'] = 'vegetarian'
    elif tag == 'Tinggi protein':
        params['minProtein'] = 20
    elif tag == 'Cepat':
        params['maxReadyTime'] = 20

    if max_ready_time:
        params['maxReadyTime'] = max_ready_time

    try:
        response = requests.get(BASE_URL, params=params, timeout=8)
        if response.status_code == 200:
            raw_data = response.json().get('results', [])
            return parse_spoonacular_data(raw_data, max_price)
    except requests.RequestException:
        pass

    return []

def parse_spoonacular_data(raw_recipes, max_price=None):
    parsed_recipes = []
    
    for item in raw_recipes:
        raw_cents = item.get('pricePerServing', 100)
        cost_idr = round(raw_cents * 150, -2)

        if max_price and cost_idr > float(max_price):
            continue

        nutrients = item.get('nutrition', {}).get('nutrients', [])
        protein_grams = 0
        for n in nutrients:
            if n.get('name') == 'Protein':
                protein_grams = round(n.get('amount', 0))
                break

        tag = 'Hemat'
        if item.get('vegetarian'):
            tag = 'Plant-based'
        elif item.get('readyInMinutes', 30) <= 20:
            tag = 'Cepat'
        elif protein_grams >= 20:
            tag = 'Tinggi protein'

        summary_text = item.get('summary', '')
        clean_summary = summary_text.replace('<b>', '').replace('</b>', '').replace('<a>', '').replace('</a>', '')

        # Parsing bahan makanan
        extended_ingredients = item.get('extendedIngredients', [])
        ingredients = [
            {
                'name': ing.get('originalName') or ing.get('name'),
                'amount': ing.get('amount'),
                'unit': ing.get('unit')
            }
            for ing in extended_ingredients
        ]

        # Parsing langkah memasak dan peralatan yang dibutuhkan
        instructions = []
        equipments_set = set()
        analyzed_instructions = item.get('analyzedInstructions', [])
        
        if analyzed_instructions:
            for step in analyzed_instructions[0].get('steps', []):
                instructions.append({
                    'number': step.get('number'),
                    'step': step.get('step')
                })
                for eq in step.get('equipment', []):
                    equipments_set.add(eq.get('name'))

        parsed_recipes.append({
            'external_api_id': item.get('id'),
            'title': item.get('title'),
            'description': clean_summary[:120] + '...' if len(clean_summary) > 120 else clean_summary,
            'image_url': item.get('image'),
            'prep_time_minutes': item.get('readyInMinutes', 15),
            'estimated_cost': cost_idr,
            'protein_grams': protein_grams,
            'is_plant_based': item.get('vegetarian', False),
            'tag': tag,
            'ingredients': ingredients,
            'equipments': list(equipments_set),
            'instructions': instructions,
        })
        
    return parsed_recipes