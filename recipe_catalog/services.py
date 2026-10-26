import requests
from django.conf import settings

SPOONACULAR_API_KEY = getattr(settings, 'SPOONACULAR_API_KEY', '')
BASE_URL = 'https://api.spoonacular.com/recipes/complexSearch'

def fetch_recipes_from_api(query='', tag='', max_ready_time=None, max_price=None, number=12):
    """
    Mengambil data resep dan informasi gizi langsung dari Spoonacular Public API.
    """
    params = {
        'apiKey': SPOONACULAR_API_KEY,
        'addRecipeInformation': 'true',
        'addRecipeNutrition': 'true',
        'number': number,
    }

    if query:
        params['query'] = query

    # Pemetaan tag Figma ke parameter filter Spoonacular API
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
        # Spoonacular menyajikan pricePerServing dalam satuan US Cents.
        # Konversi estimasi: 1 Cent USD ≈ Rp150 IDR (dibulatkan ke ratusan terdekat)
        raw_cents = item.get('pricePerServing', 100)
        cost_idr = round(raw_cents * 150, -2)

        if max_price and cost_idr > float(max_price):
            continue

        # Ekstraksi nilai gizi protein dari array nutrisi API
        nutrients = item.get('nutrition', {}).get('nutrients', [])
        protein_grams = 0
        for n in nutrients:
            if n.get('name') == 'Protein':
                protein_grams = round(n.get('amount', 0))
                break

        # Penentuan label kategori (tag) berdasarkan data dari API
        tag = 'Hemat'
        if item.get('vegetarian'):
            tag = 'Plant-based'
        elif item.get('readyInMinutes', 30) <= 20:
            tag = 'Cepat'
        elif protein_grams >= 20:
            tag = 'Tinggi protein'

        # Pembersihan tag HTML dari summary deskripsi Spoonacular
        summary_text = item.get('summary', '')
        clean_summary = summary_text.replace('<b>', '').replace('</b>', '').replace('<a>', '').replace('</a>', '')

        parsed_recipes.append({
            'id': item.get('id'),
            'title': item.get('title'),
            'description': clean_summary[:120] + '...' if len(clean_summary) > 120 else clean_summary,
            'image_url': item.get('image'),
            'prep_time_minutes': item.get('readyInMinutes', 15),
            'estimated_cost': cost_idr,
            'estimated_cost_formatted': f"Rp{cost_idr:,.0f}".replace(',', '.'),
            'protein_grams': protein_grams,
            'tag': tag,
            'source_url': item.get('sourceUrl', '#'),
        })
        
    return parsed_recipes