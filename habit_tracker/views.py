import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Habit, HabitLog, SleepLog
from .forms import HabitForm

@login_required(login_url='/auth/login/')
def habit_tracker_view(request):
    return render(request, 'habit_tracker.html')

@login_required
@require_GET
def get_habits_json(request):
    today = timezone.now().date()
    habits = Habit.objects.filter(user=request.user)
    
    habits_data = []
    completed_count = 0

    for habit in habits:
        log, _ = HabitLog.objects.get_or_create(habit=habit, date=today)
        if log.is_completed:
            completed_count += 1

        habits_data.append({
            'id': habit.id,
            'title': habit.title,
            'category': habit.category,
            'target_value': habit.target_value,
            'unit': habit.unit,
            'current_value': log.current_value,
            'is_completed': log.is_completed,
            'logged_time': log.logged_time.strftime('%H.%M') if log.logged_time else ''
        })

    total_habits = len(habits_data)
    progress_percent = int((completed_count / total_habits * 100)) if total_habits > 0 else 0

    return JsonResponse({
        'habits': habits_data,
        'summary': {
            'total': total_habits,
            'completed': completed_count,
            'progress_percent': progress_percent,
            'streak': 6, # Contoh data dynamic agregat
            'energy_score': 8,
            'focus_time': "3j 15m"
        }
    }, status=200)

@login_required
@require_POST
def add_habit_ajax(request):
    form = HabitForm(request.POST)
    if form.is_valid():
        habit = form.save(commit=False)
        habit.user = request.user
        habit.save()
        return JsonResponse({'message': 'Kebiasaan berhasil ditambahkan!'}, status=201)
    return JsonResponse({'errors': form.errors.get_json_data()}, status=400)

@login_required
@require_POST
def toggle_habit_ajax(request, habit_id):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    today = timezone.now().date()
    log, _ = HabitLog.objects.get_or_create(habit=habit, date=today)
    
    log.is_completed = not log.is_completed
    if log.is_completed:
        log.current_value = habit.target_value
    else:
        log.current_value = 0
    log.save()

    return JsonResponse({
        'message': 'Status kebiasaan diperbarui',
        'is_completed': log.is_completed
    }, status=200)

@login_required
@require_POST
def delete_habit_ajax(request, habit_id):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    habit.delete()
    return JsonResponse({'message': 'Kebiasaan berhasil dihapus'}, status=200)