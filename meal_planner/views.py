from datetime import date, timedelta
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from . import nutrition
from .forms import MealForm
from .models import Meal

HARI = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
# Urutan tampil dalam sehari: sarapan -> siang -> malam -> camilan
MEAL_ORDER = {value: i for i, (value, _) in enumerate(Meal.MealType.choices)}


def _parse_date(value, default):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return default


def _user(request):
    # SEMENTARA (tanpa login): pakai user 'demo' kalau belum login.
    # TODO: hapus fungsi ini & pasang lagi @login_required kalau modul autentikasi sudah ada.
    if request.user.is_authenticated:
        return request.user
    user, _ = get_user_model().objects.get_or_create(username='demo')
    return user


def _monday(d):
    return d - timedelta(days=d.weekday())


def _planner_url(d):
    """URL planner untuk minggu yang memuat tanggal d."""
    return f"{reverse('meal_planner:index')}?start={_monday(d).isoformat()}"


def planner(request):
    today = timezone.localdate()
    start = _monday(_parse_date(request.GET.get('start'), today))
    end = start + timedelta(days=6)

    meals = list(Meal.objects.filter(user=_user(request), date__range=(start, end)))
    by_date = {}
    for meal in meals:
        by_date.setdefault(meal.date, []).append(meal)

    days = []
    for i in range(7):
        d = start + timedelta(days=i)
        day_meals = sorted(by_date.get(d, []), key=lambda m: MEAL_ORDER[m.meal_type])
        days.append({
            'date': d,
            'label': HARI[i],
            'is_today': d == today,
            'meals': day_meals,
            'cost': sum(m.estimated_cost for m in day_meals),
        })

    return render(request, 'planner.html', {
        'days': days,
        'start': start,
        'end': end,
        'prev_start': (start - timedelta(days=7)).isoformat(),
        'next_start': (start + timedelta(days=7)).isoformat(),
        'week_cost': sum(m.estimated_cost for m in meals),
        'week_meal_count': len(meals),
        'week_homemade_count': sum(1 for m in meals if m.is_homemade),
        'week_packaging_avoided': sum(m.packaging_avoided for m in meals),
    })


def meal_create(request):
    initial_date = _parse_date(request.GET.get('date'), timezone.localdate())
    form = MealForm(request.POST or None, initial={'date': initial_date})
    if request.method == 'POST' and form.is_valid():
        meal = form.save(commit=False)
        meal.user = _user(request)
        meal.save()
        messages.success(request, 'Menu berhasil ditambahkan.')
        return redirect(_planner_url(meal.date))
    return render(request, 'meal_form.html', {'form': form})


@require_POST
def meal_delete(request, pk):
    # filter user: user cuma bisa hapus menu miliknya sendiri
    meal = get_object_or_404(Meal, pk=pk, user=_user(request))
    meal_date = meal.date
    meal.delete()
    messages.success(request, 'Menu dihapus.')
    return redirect(_planner_url(meal_date))


@require_POST
def estimate_calories(request):
    """Dipanggil dari form lewat JavaScript. Mengembalikan JSON."""
    try:
        result = nutrition.estimate_total(request.POST.get('ingredients', ''))
    except nutrition.NutritionError as e:
        return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse(result)