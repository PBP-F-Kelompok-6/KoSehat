from datetime import date, timedelta
from types import SimpleNamespace

from django.shortcuts import render


HARI = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']


def _meal(tipe, name, cost, calories=None, homemade=False, packaging=0):
    """Membuat objek menu sementara (dummy) dengan atribut yang sama seperti model Meal."""
    return SimpleNamespace(
        get_meal_type_display=tipe, name=name, estimated_cost=cost,
        calories=calories, is_homemade=homemade, packaging_avoided=packaging,
    )



DUMMY_MEALS = {
   
    
}


def planner(request):
    today = date.today()
    start = today - timedelta(days=today.weekday())

    days = []
    for i in range(7):
        d = start + timedelta(days=i)
        meals = DUMMY_MEALS.get(i, [])
        days.append({
            'date': d, 'label': HARI[i], 'is_today': d == today,
            'meals': meals, 'cost': sum(m.estimated_cost for m in meals),
        })
    all_meals = [m for d in days for m in d['meals']]

    return render(request, 'planner.html', {
        'days': days,
        'start': start,
        'end': start + timedelta(days=6),
        'week_cost': sum(d['cost'] for d in days),
        'week_meal_count': len(all_meals),
        'week_homemade_count': sum(1 for m in all_meals if m.is_homemade),
        'week_packaging_avoided': sum(m.packaging_avoided for m in all_meals),
    })