from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import nutrition
from .forms import MealForm
from .models import Meal

HARI = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
# Urutan tampil dalam sehari: sarapan -> siang -> malam -> camilan
# (.get(..., 99) jaga-jaga kalau ada tipe yang nggak dikenal, supaya halaman nggak error)
MEAL_ORDER = {value: i for i, (value, _) in enumerate(Meal.MealType.choices)}


def _parse_date(value, default):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return default


def _monday(d):
    return d - timedelta(days=d.weekday())


def _eco_message(meal_count, homemade_count, packaging_used):
    """Kalimat singkat di bawah ringkasan, menyesuaikan data minggu itu."""
    if meal_count == 0:
        return 'Belum ada menu di minggu ini. Yuk mulai rencanakan!'
    if homemade_count == 0:
        return 'Belum ada menu masak sendiri di minggu ini. Coba satu dulu, dompet dan bumi sama-sama senang.'
    if packaging_used == 0:
        return f'Mantap! {homemade_count} dari {meal_count} menu masak sendiri dan tanpa kemasan plastik.'
    return f'Mantap, {homemade_count} dari {meal_count} menu masak sendiri di minggu ini.'


def _eco_image(meal_count, homemade_count, packaging_used):
    """Ilustrasi tanaman yang 'tumbuh' mengikuti progres eco-diet minggu itu."""
    if meal_count == 0 or homemade_count == 0:
        return 'img/eco-seed.svg'
    if packaging_used == 0:
        return 'img/eco-bloom.svg'
    return 'img/eco-sprout.svg'


def _planner_url(d):
    """URL planner untuk minggu yang memuat tanggal d."""
    return f"{reverse('meal_planner:index')}?start={_monday(d).isoformat()}"


@login_required
def planner(request):
    today = timezone.localdate()
    start = _monday(_parse_date(request.GET.get('start'), today))
    end = start + timedelta(days=6)

    meals = list(Meal.objects.filter(user=request.user, date__range=(start, end)))
    by_date = {}
    for meal in meals:
        by_date.setdefault(meal.date, []).append(meal)

    days = []
    for i in range(7):
        d = start + timedelta(days=i)
        day_meals = sorted(by_date.get(d, []), key=lambda m: MEAL_ORDER.get(m.meal_type, 99))
        days.append({
            'date': d,
            'label': HARI[i],
            'is_today': d == today,
            'is_past': d < today,
            'meals': day_meals,
            'cost': sum(m.estimated_cost for m in day_meals),
        })

    return render(request, 'planner.html', {
        'days': days,
        'start': start,
        'end': end,
        'prev_start': (start - timedelta(days=7)).isoformat(),
        'is_current_week': start == _monday(today),
        'current_start': _monday(today).isoformat(),
        'next_start': (start + timedelta(days=7)).isoformat(),
        'week_cost': sum(m.estimated_cost for m in meals),
        'week_meal_count': len(meals),
        'week_homemade_count': sum(1 for m in meals if m.is_homemade),
        'week_packaging_used': sum(m.packaging_used for m in meals),
        'homemade_percent': round(100 * sum(1 for m in meals if m.is_homemade) / len(meals)) if meals else 0,
        'eco_image': _eco_image(
            len(meals),
            sum(1 for m in meals if m.is_homemade),
            sum(m.packaging_used for m in meals),
        ),
        'eco_message': _eco_message(
            len(meals),
            sum(1 for m in meals if m.is_homemade),
            sum(m.packaging_used for m in meals),
        ),
    })


@login_required
def meal_create(request):
    initial_date = _parse_date(request.GET.get('date'), timezone.localdate())
    form = MealForm(request.POST or None, initial={'date': initial_date})
    if request.method == 'POST' and form.is_valid():
        meal = form.save(commit=False)
        meal.user = request.user
        meal.save()
        messages.success(request, 'Menu berhasil ditambahkan.')
        return redirect(_planner_url(meal.date))
    return render(request, 'meal_form.html', {'form': form, 'title': 'Tambah Menu'})


@login_required
def meal_update(request, pk):
    # filter user: user cuma bisa mengubah menu miliknya sendiri
    meal = get_object_or_404(Meal, pk=pk, user=request.user)
    form = MealForm(request.POST or None, instance=meal)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Menu berhasil diperbarui.')
        return redirect(_planner_url(meal.date))
    return render(request, 'meal_form.html', {'form': form, 'title': 'Ubah Menu'})


@login_required
@require_POST
def meal_delete(request, pk):
    # filter user: user cuma bisa hapus menu miliknya sendiri
    meal = get_object_or_404(Meal, pk=pk, user=request.user)
    meal_date = meal.date
    meal.delete()
    messages.success(request, 'Menu dihapus.')
    return redirect(_planner_url(meal_date))


@require_POST
def estimate_calories(request):
    """Dipanggil dari form lewat JavaScript. Mengembalikan JSON."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Silakan login dulu.'}, status=401)
    try:
        result = nutrition.estimate_total(request.POST.get('ingredients', ''))
    except nutrition.NutritionError as e:
        return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse(result)