import json
from datetime import timedelta
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Habit, HabitLog, SleepLog, EnergyLog, UserStreak
from .forms import HabitForm, EnergyLogForm, AddFocusTimeForm, SleepSettingForm

DAY_INITIALS = {0: 'S', 1: 'S', 2: 'R', 3: 'K', 4: 'J', 5: 'S', 6: 'M'}

def get_or_update_user_streak(user, today):
    streak_obj, created = UserStreak.objects.get_or_create(user=user)

    if created or streak_obj.last_checked_date is None:
        streak_obj.last_checked_date = today
        streak_obj.save()
        return streak_obj

    if streak_obj.last_checked_date >= today:
        return streak_obj

    check_date = streak_obj.last_checked_date
    current_streak = streak_obj.current_streak
    best_streak = streak_obj.best_streak

    # Evaluasi setiap hari dari last_checked_date sampai kemarin (today - 1 hari)
    while check_date < today:
        habits_on_date = Habit.objects.filter(user=user, created_at__date__lte=check_date)
        
        if habits_on_date.exists():
            total_habits = habits_on_date.count()
            completed_logs = HabitLog.objects.filter(
                habit__in=habits_on_date,
                date=check_date,
                is_completed=True
            ).count()

            if completed_logs >= total_habits and total_habits > 0:
                current_streak += 1
                if current_streak > best_streak:
                    best_streak = current_streak
            else:
                current_streak = 0

        check_date += timedelta(days=1)

    streak_obj.current_streak = current_streak
    streak_obj.best_streak = best_streak
    streak_obj.last_checked_date = today
    streak_obj.save()

    return streak_obj

def format_minutes(total_minutes):
    """Mengubah durasi menit menjadi format string 'Xj Ym' atau 'Ym'."""
    if total_minutes is None or total_minutes < 0:
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

    streak_obj = get_or_update_user_streak(request.user, today)
    energy_log, _ = EnergyLog.objects.get_or_create(user=request.user, date=today)
    
    target_mins = energy_log.focus_minutes
    logged_mins = energy_log.logged_focus_minutes
    is_target_reached = logged_mins >= target_mins and target_mins > 0

    # Data Kualitas Tidur 7 Malam Terakhir
    default_sample_durations = [390, 430, 400, 460, 420, 480, 444] # Data dummy variatif untuk 7 malam
    sleep_bars = []
    
    target_sleep_hours = 7.5
    latest_sleep_log, _ = SleepLog.objects.get_or_create(user=request.user, date=today)
    target_sleep_hours = latest_sleep_log.target_hours

    for i in range(6, -1, -1):
        day_date = today - timedelta(days=i)
        s_log, created = SleepLog.objects.get_or_create(user=request.user, date=day_date)
        
        if created:
            s_log.duration_minutes = default_sample_durations[6 - i]
            s_log.target_hours = target_sleep_hours
            s_log.save()

        # Hitung tinggi bar dalam persentase
        max_scale_mins = max(target_sleep_hours * 60 * 1.25, 600) # Skala maksimal sekitar 10 jam
        height_pct = max(10, min(100, int((s_log.duration_minutes / max_scale_mins) * 100)))

        sleep_bars.append({
            'date': day_date.strftime('%Y-%m-%d'),
            'day_initial': DAY_INITIALS[day_date.weekday()],
            'duration_minutes': s_log.duration_minutes,
            'duration_str': format_minutes(s_log.duration_minutes),
            'height_percent': height_pct,
            'is_latest': (i == 0)
        })

    latest_duration_str = format_minutes(latest_sleep_log.duration_minutes)
    target_hours_formatted = f"{latest_sleep_log.target_hours:g}".replace('.', ',')

    return JsonResponse({
        'habits': habits_data,
        'summary': {
            'total': total_habits,
            'completed': completed_count,
            'progress_percent': progress_percent,
            'streak': streak_obj.current_streak,
            'best_streak': streak_obj.best_streak,
            'energy_level': energy_log.energy_level,
            'target_focus_minutes': target_mins,
            'logged_focus_minutes': logged_mins,
            'focus_time_str': format_minutes(logged_mins),
            'target_focus_str': format_minutes(target_mins),
            'is_target_reached': is_target_reached,
            'sleep': {
                'last_night_str': latest_duration_str,
                'last_night_hours': latest_sleep_log.duration_minutes // 60,
                'last_night_mins': latest_sleep_log.duration_minutes % 60,
                'target_hours': latest_sleep_log.target_hours,
                'target_str': f"{target_hours_formatted} jam",
                'bars': sleep_bars,
            }
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

@login_required
@require_POST
def log_sleep_settings_ajax(request):
    form = SleepSettingForm(request.POST)
    if form.is_valid():
        today = timezone.now().date()
        target_h = form.cleaned_data['target_hours']
        sleep_h = form.cleaned_data['sleep_hours']
        sleep_m = form.cleaned_data['sleep_minutes']
        total_mins = (sleep_h * 60) + sleep_m

        # Perbarui log hari ini
        sleep_log, _ = SleepLog.objects.get_or_create(user=request.user, date=today)
        sleep_log.target_hours = target_h
        sleep_log.duration_minutes = total_mins
        sleep_log.save()

        # Update target_hours pada log 7 hari terakhir agar konsisten
        for i in range(1, 7):
            past_date = today - timedelta(days=i)
            SleepLog.objects.filter(user=request.user, date=past_date).update(target_hours=target_h)

        return JsonResponse({
            'message': 'Pengaturan & catatan tidur berhasil disimpan!',
            'last_night_str': format_minutes(total_mins),
        }, status=200)
        
    return JsonResponse({'errors': form.errors.get_json_data()}, status=400)