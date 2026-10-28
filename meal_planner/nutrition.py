
import requests
from django.conf import settings

SEARCH_URL = 'https://api.nal.usda.gov/fdc/v1/foods/search'
MAX_LINES = 10  # jaga-jaga supaya kuota API nggak cepat habis


class NutritionError(Exception):
    """Error yang pesannya aman ditampilkan ke user."""


def kcal_per_100g(query):
    """Kembalikan (nama_makanan_di_usda, kkal_per_100g) untuk satu bahan."""
    if not settings.USDA_API_KEY:
        raise NutritionError('API key USDA belum diatur di file .env.')
    try:
        resp = requests.get(
            SEARCH_URL,
            params={
                'api_key': settings.USDA_API_KEY,
                'query': query,
                'pageSize': 1,
                # Foundation & SR Legacy: nilai gizi per 100 g
                'dataType': 'Foundation,SR Legacy',
            },
            timeout=8,
        )
        resp.raise_for_status()
    except requests.RequestException:
        raise NutritionError('Gagal menghubungi layanan nutrisi, coba lagi nanti.')

    foods = resp.json().get('foods', [])
    if not foods:
        raise NutritionError(f'"{query}" tidak ditemukan. Coba nama bahan dalam bahasa Inggris.')

    food = foods[0]
    for nutrient in food.get('foodNutrients', []):
        name = nutrient.get('nutrientName', '')
        unit = nutrient.get('unitName', '').upper()
        if name.startswith('Energy') and unit == 'KCAL':
            return food.get('description', query), float(nutrient['value'])
    raise NutritionError(f'Data kalori untuk "{query}" tidak tersedia.')


def estimate_total(text):
    """Parse beberapa baris 'nama, gram' lalu jumlahkan kalorinya."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise NutritionError('Isi dulu bahannya, satu bahan per baris.')
    if len(lines) > MAX_LINES:
        raise NutritionError(f'Maksimal {MAX_LINES} bahan per perhitungan.')

    items, total = [], 0.0
    for line in lines:
        try:
            name, grams_text = [part.strip() for part in line.rsplit(',', 1)]
            grams = float(grams_text)
            if not name or grams <= 0:
                raise ValueError
        except ValueError:
            raise NutritionError(f'Format salah: "{line}". Contoh: white rice cooked, 150')
        matched_name, per_100g = kcal_per_100g(name)
        kcal = per_100g * grams / 100
        total += kcal
        items.append({'name': matched_name, 'grams': grams, 'kcal': round(kcal)})
    return {'kcal': round(total), 'items': items}