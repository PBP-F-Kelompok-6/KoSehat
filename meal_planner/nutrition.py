"""Hitung kalori otomatis lewat USDA FoodData Central.

Input: baris "nama bahan (bahasa Inggris), gram", mis. "white rice cooked, 150".
Hasilnya perkiraan, bukan angka pasti.
"""
import re

import requests
from django.conf import settings

SEARCH_URL = 'https://api.nal.usda.gov/fdc/v1/foods/search'
MAX_LINES = 10  # jaga-jaga supaya kuota API nggak cepat habis


class NutritionError(Exception):
    """Error yang pesannya aman ditampilkan ke user."""


SEARCH_SIZE = 10  # ambil beberapa kandidat, lalu pilih yang paling cocok

# Varian khusus: dihindari kecuali user menyebutkannya sendiri di nama bahan
VARIANT_WORDS = {
    'glutinous', 'wild', 'instant', 'flavored', 'mix', 'mixed', 'fried',
    'babyfood', 'canned', 'dehydrated', 'dry', 'frozen', 'restaurant',
    'pudding', 'flour', 'bran', 'noodle', 'cake', 'cracker',
    'spread', 'sandwich', 'salad', 'soup', 'sauce', 'nugget', 'patty',
    'luncheon', 'gravy', 'pie',
    'meatless', 'vegetarian', 'imitation',
}
# USDA menandai varian standar/umum dengan kata ini (mis. "Rice, white, ..., regular, cooked")
DEFAULT_WORDS = {'regular'}


def _tokens(text):
    """Pecah teks jadi kumpulan kata kecil (plural sederhana dibuang)."""
    words = re.findall(r'[a-z]+', text.lower())
    return {w[:-1] if len(w) > 3 and w.endswith('s') else w for w in words}


# Daftar kata di atas dipecah dengan cara yang sama seperti teks lain,
# supaya perbandingannya cocok (mis. 'meatless' -> 'meatles' di kedua sisi).
_VARIANT_TOKENS = _tokens(' '.join(VARIANT_WORDS))
_DEFAULT_TOKENS = _tokens(' '.join(DEFAULT_WORDS))


def _energy_kcal(food):
    for nutrient in food.get('foodNutrients', []):
        name = nutrient.get('nutrientName', '')
        unit = nutrient.get('unitName', '').upper()
        if name.startswith('Energy') and unit == 'KCAL':
            return float(nutrient['value'])
    return None


def _score(query_tokens, description, rank):
    """Makin tinggi makin cocok. rank = urutan hasil dari USDA (0 = paling atas)."""
    desc = _tokens(description)
    matched = len(query_tokens & desc)
    missing = len(query_tokens - desc)
    penalty = len((desc & _VARIANT_TOKENS) - query_tokens)
    bonus = len(desc & _DEFAULT_TOKENS)
    return matched * 3 - missing * 3 - penalty * 4 + bonus * 2 - rank * 0.1


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
                'pageSize': SEARCH_SIZE,
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

    query_tokens = _tokens(query)
    best = None  # (skor, deskripsi, kkal)
    for rank, food in enumerate(foods):
        kcal = _energy_kcal(food)
        if kcal is None:
            continue
        description = food.get('description', query)
        score = _score(query_tokens, description, rank)
        if best is None or score > best[0]:
            best = (score, description, kcal)
    if best is None:
        raise NutritionError(f'Data kalori untuk "{query}" tidak tersedia.')
    return best[1], best[2]


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
        items.append({
            'name': matched_name,
            'grams': grams,
            'per_100g': round(per_100g),
            'kcal': round(kcal),
        })
    return {'kcal': round(total), 'items': items}