import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Habit, HabitLog, SleepLog, EnergyLog
from .forms import HabitForm, EnergyLogForm, AddFocusTimeForm


def format_minutes(total_minutes):
    """Mengubah durasi menit menjadi format string 'Xj Ym' atau 'Ym'."""
    if total_minutes is None:
        total_minutes = 0
    hours = total_minutes // 60
    mins = total_minutes % 60
    if hours > 0 and mins > 0:
        return f"{hours}j {mins}m"
    elif hours > 0:
        return f"{hours}j"
    else:
        return f"{mins}m"


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

    energy_log, _ = EnergyLog.objects.get_or_create(user=request.user, date=today)
    
    target_mins = energy_log.focus_minutes
    logged_mins = energy_log.logged_focus_minutes
    is_target_reached = logged_mins >= target_mins and target_mins > 0

    return JsonResponse({
        'habits': habits_data,
        'summary': {
            'total': total_habits,
            'completed': completed_count,
            'progress_percent': progress_percent,
            'energy_level': energy_log.energy_level,
            'target_focus_minutes': target_mins,
            'logged_focus_minutes': logged_mins,
            'focus_time_str': format_minutes(logged_mins),
            'target_focus_str': format_minutes(target_mins),
            'is_target_reached': is_target_reached,
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
    log.current_value = habit.target_value if log.is_completed else 0
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

@login_required
@require_POST
def log_energy_ajax(request):
    today = timezone.now().date()
    energy_log, _ = EnergyLog.objects.get_or_create(user=request.user, date=today)
    
    form = EnergyLogForm(request.POST, instance=energy_log)
    if form.is_valid():
        form.save()
        return JsonResponse({'message': 'Refleksi energi & fokus berhasil disimpan!'}, status=200)
    return JsonResponse({'errors': form.errors.get_json_data()}, status=400)

@login_required
@require_POST
def add_focus_time_ajax(request):
    form = AddFocusTimeForm(request.POST)
    if form.is_valid():
        today = timezone.now().date()
        energy_log, _ = EnergyLog.objects.get_or_create(user=request.user, date=today)
        
        additional = form.cleaned_data['additional_minutes']
        energy_log.logged_focus_minutes += additional
        energy_log.save()
        
        is_target_reached = energy_log.logged_focus_minutes >= energy_log.focus_minutes and energy_log.focus_minutes > 0
        
        return JsonResponse({
            'message': f'Berhasil menambah {additional} menit fokus!',
            'logged_focus_minutes': energy_log.logged_focus_minutes,
            'focus_time_str': format_minutes(energy_log.logged_focus_minutes),
            'is_target_reached': is_target_reached,
        }, status=200)
    return JsonResponse({'errors': form.errors.get_json_data()}, status=400)