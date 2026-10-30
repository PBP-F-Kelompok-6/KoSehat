from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .forms import (
    AddFocusTimeForm,
    AddHabitProgressForm,
    EnergyLogForm,
    HabitForm,
    HydrationForm,
    SleepSettingForm,
)
from .models import (
    EnergyLog,
    Habit,
    HabitLog,
    HydrationLog,
    SleepLog,
    UserStreak,
)


DAY_INITIALS = {
    0: "Sen",
    1: "Sel",
    2: "Rab",
    3: "Kam",
    4: "Jum",
    5: "Sab",
    6: "Min",
}


def format_minutes(total_minutes):
    total_minutes = max(total_minutes or 0, 0)
    hours = total_minutes // 60
    minutes = total_minutes % 60

    if hours and minutes:
        return f"{hours}j {minutes}m"
    if hours:
        return f"{hours}j"
    return f"{minutes}m"


def get_selected_date(request):
    raw_date = request.GET.get("date")

    if not raw_date:
        return timezone.localdate()

    try:
        return timezone.datetime.strptime(
            raw_date,
            "%Y-%m-%d",
        ).date()
    except ValueError:
        return timezone.localdate()


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

    while check_date < today:
        habits_on_date = Habit.objects.filter(
            user=user,
            created_at__date__lte=check_date,
        )

        if not habits_on_date.exists():
            current_streak = 0
        else:
            completed_count = HabitLog.objects.filter(
                habit__in=habits_on_date,
                date=check_date,
                is_completed=True,
            ).count()

            if completed_count == habits_on_date.count():
                current_streak += 1
                best_streak = max(best_streak, current_streak)
            else:
                current_streak = 0

        check_date += timedelta(days=1)

    streak_obj.current_streak = current_streak
    streak_obj.best_streak = best_streak
    streak_obj.last_checked_date = today
    streak_obj.save()

    return streak_obj


@login_required(login_url="/auth/login/")
def habit_tracker_view(request):
    return render(request, "habit_tracker.html")


@login_required
@require_GET
def get_habits_json(request):
    selected_date = get_selected_date(request)
    user = request.user

    habits = Habit.objects.filter(
        user=user,
        is_active=True,
    ).order_by("created_at")

    habits_data = []
    completed_count = 0

    for habit in habits:
        log, _ = HabitLog.objects.get_or_create(
            habit=habit,
            date=selected_date,
        )

        if log.is_completed:
            completed_count += 1

        habits_data.append(
            {
                "id": habit.id,
                "title": habit.title,
                "category": habit.category,
                "target_value": habit.target_value,
                "unit": habit.unit,
                "current_value": log.current_value,
                "progress_percent": log.progress_percent,
                "is_completed": log.is_completed,
                "logged_time": (
                    log.logged_time.strftime("%H.%M")
                    if log.logged_time
                    else ""
                ),
            }
        )

    total_habits = len(habits_data)
    progress_percent = (
        int(completed_count / total_habits * 100)
        if total_habits
        else 0
    )

    streak_obj = get_or_update_user_streak(
        user,
        timezone.localdate(),
    )

    energy_log, _ = EnergyLog.objects.get_or_create(
        user=user,
        date=selected_date,
    )

    hydration_log, _ = HydrationLog.objects.get_or_create(
        user=user,
        date=selected_date,
        defaults={"target_ml": 2500},
    )

    if hydration_log.target_ml != 2500:
        hydration_log.target_ml = 2500
        hydration_log.save(update_fields=["target_ml", "updated_at"])

    sleep_bars = []
    latest_sleep_log, _ = SleepLog.objects.get_or_create(
        user=user,
        date=selected_date,
    )

    target_sleep_hours = latest_sleep_log.target_hours

    for index in range(6, -1, -1):
        day_date = selected_date - timedelta(days=index)
        sleep_log = SleepLog.objects.filter(
            user=user,
            date=day_date,
        ).first()

        if sleep_log is None:
            duration_minutes = 0
            day_target_sleep_hours = target_sleep_hours
        else:
            duration_minutes = sleep_log.duration_minutes
            day_target_sleep_hours = sleep_log.target_hours

        max_scale_minutes = max(
            day_target_sleep_hours * 60 * 1.25,
            600,
        )

        height_percent = max(
            0,
            min(
                100,
                int(
                    duration_minutes
                    / max_scale_minutes
                    * 100
                ),
            ),
        )

        sleep_bars.append(
            {
                "date": day_date.isoformat(),
                "day_initial": DAY_INITIALS[day_date.weekday()],
                "duration_minutes": duration_minutes,
                "duration_str": format_minutes(
                    duration_minutes,
                ),
                "height_percent": height_percent,
                "is_latest": index == 0,
            }
        )

    current_date = timezone.localdate()
    monday = current_date - timedelta(days=current_date.weekday())
    weekly_consistency = []

    for day_offset in range(7):
        consistency_date = monday + timedelta(days=day_offset)
        habits_for_day = Habit.objects.filter(
            user=user,
            created_at__date__lte=consistency_date,
        )
        total_for_day = habits_for_day.count()
        completed_for_day = HabitLog.objects.filter(
            habit__in=habits_for_day,
            date=consistency_date,
            is_completed=True,
        ).count()

        consistency_percent = (
            round(completed_for_day / total_for_day * 100)
            if total_for_day
            else 0
        )

        weekly_consistency.append(
            {
                "date": consistency_date.isoformat(),
                "day_name": DAY_INITIALS[consistency_date.weekday()],
                "percent": consistency_percent,
                "is_current": consistency_date == current_date,
                "is_future": consistency_date > current_date,
            }
        )

    return JsonResponse(
        {
            "selected_date": selected_date.isoformat(),
            "habits": habits_data,
            "summary": {
                "total": total_habits,
                "completed": completed_count,
                "progress_percent": progress_percent,
                "streak": streak_obj.current_streak,
                "best_streak": streak_obj.best_streak,
                "target_focus_minutes": energy_log.focus_minutes,
                "logged_focus_minutes": (
                    energy_log.logged_focus_minutes
                ),
                "focus_time_str": format_minutes(
                    energy_log.logged_focus_minutes,
                ),
                "target_focus_str": format_minutes(
                    energy_log.focus_minutes,
                ),
                "is_target_reached": (
                    energy_log.focus_target_reached
                ),
                "hydration": {
                    "amount_ml": hydration_log.amount_ml,
                    "target_ml": hydration_log.target_ml,
                    "remaining_ml": hydration_log.remaining_ml,
                    "progress_percent": (
                        hydration_log.progress_percent
                    ),
                    "target_reached": hydration_log.target_reached,
                },
                "weekly_consistency": weekly_consistency,
                "sleep": {
                    "last_night_str": format_minutes(
                        latest_sleep_log.duration_minutes,
                    ),
                    "last_night_hours": (
                        latest_sleep_log.duration_minutes // 60
                    ),
                    "last_night_mins": (
                        latest_sleep_log.duration_minutes % 60
                    ),
                    "target_hours": latest_sleep_log.target_hours,
                    "target_str": (
                        f"{latest_sleep_log.target_hours:g} jam"
                    ),
                    "status": latest_sleep_log.sleep_status,
                    "bars": sleep_bars,
                },
            },
        }
    )


@login_required
@require_POST
def add_habit_ajax(request):
    form = HabitForm(request.POST)

    if not form.is_valid():
        return JsonResponse(
            {"errors": form.errors.get_json_data()},
            status=400,
        )

    habit = form.save(commit=False)
    habit.user = request.user
    habit.save()

    return JsonResponse(
        {
            "message": "Kebiasaan berhasil ditambahkan.",
            "habit_id": habit.id,
        },
        status=201,
    )


@login_required
@require_POST
def toggle_habit_ajax(request, habit_id):
    habit = get_object_or_404(
        Habit,
        id=habit_id,
        user=request.user,
        is_active=True,
    )

    selected_date = get_selected_date(request)

    log, _ = HabitLog.objects.get_or_create(
        habit=habit,
        date=selected_date,
    )

    if log.is_completed:
        log.current_value = 0
    else:
        log.current_value = habit.target_value

    log.save()

    return JsonResponse(
        {
            "message": "Status kebiasaan diperbarui.",
            "is_completed": log.is_completed,
            "current_value": log.current_value,
            "progress_percent": log.progress_percent,
        }
    )


@login_required
@require_POST
def add_habit_progress_ajax(request, habit_id):
    habit = get_object_or_404(
        Habit,
        id=habit_id,
        user=request.user,
        is_active=True,
    )

    form = AddHabitProgressForm(request.POST)

    if not form.is_valid():
        return JsonResponse(
            {"errors": form.errors.get_json_data()},
            status=400,
        )

    selected_date = get_selected_date(request)

    log, _ = HabitLog.objects.get_or_create(
        habit=habit,
        date=selected_date,
    )

    log.current_value += form.cleaned_data["additional_value"]
    log.save()

    return JsonResponse(
        {
            "message": "Progress kebiasaan diperbarui.",
            "current_value": log.current_value,
            "progress_percent": log.progress_percent,
            "is_completed": log.is_completed,
        }
    )


@login_required
@require_POST
def delete_habit_ajax(request, habit_id):
    habit = get_object_or_404(
        Habit,
        id=habit_id,
        user=request.user,
        is_active=True,
    )

    habit.archive()

    return JsonResponse(
        {"message": "Kebiasaan berhasil diarsipkan."}
    )


@login_required
@require_POST
def log_energy_ajax(request):
    selected_date = get_selected_date(request)

    energy_log, _ = EnergyLog.objects.get_or_create(
        user=request.user,
        date=selected_date,
    )

    form = EnergyLogForm(
        request.POST,
        instance=energy_log,
    )

    if not form.is_valid():
        return JsonResponse(
            {"errors": form.errors.get_json_data()},
            status=400,
        )

    form.save()

    return JsonResponse(
        {"message": "Energi dan target fokus berhasil disimpan."}
    )


@login_required
@require_POST
def add_focus_time_ajax(request):
    form = AddFocusTimeForm(request.POST)

    if not form.is_valid():
        return JsonResponse(
            {"errors": form.errors.get_json_data()},
            status=400,
        )

    selected_date = get_selected_date(request)

    energy_log, _ = EnergyLog.objects.get_or_create(
        user=request.user,
        date=selected_date,
    )

    energy_log.logged_focus_minutes += (
        form.cleaned_data["additional_minutes"]
    )
    energy_log.save()

    return JsonResponse(
        {
            "message": "Waktu fokus berhasil ditambahkan.",
            "logged_focus_minutes": (
                energy_log.logged_focus_minutes
            ),
            "focus_time_str": format_minutes(
                energy_log.logged_focus_minutes,
            ),
            "is_target_reached": (
                energy_log.focus_target_reached
            ),
        }
    )


@login_required
@require_POST
def log_sleep_settings_ajax(request):
    form = SleepSettingForm(request.POST)

    if not form.is_valid():
        return JsonResponse(
            {"errors": form.errors.get_json_data()},
            status=400,
        )

    selected_date = get_selected_date(request)

    duration_minutes = (
        form.cleaned_data["sleep_hours"] * 60
        + form.cleaned_data["sleep_minutes"]
    )

    sleep_log, _ = SleepLog.objects.get_or_create(
        user=request.user,
        date=selected_date,
    )

    sleep_log.target_hours = form.cleaned_data["target_hours"]
    sleep_log.duration_minutes = duration_minutes
    sleep_log.save()

    return JsonResponse(
        {
            "message": "Catatan tidur berhasil disimpan.",
            "last_night_str": format_minutes(duration_minutes),
            "status": sleep_log.sleep_status,
        }
    )


@login_required
@require_POST
def add_hydration_ajax(request):
    form = HydrationForm(request.POST)

    if not form.is_valid():
        return JsonResponse(
            {"errors": form.errors.get_json_data()},
            status=400,
        )

    selected_date = get_selected_date(request)

    hydration_log, _ = HydrationLog.objects.get_or_create(
        user=request.user,
        date=selected_date,
    )

    hydration_log.amount_ml += form.cleaned_data["amount_ml"]

    hydration_log.save()

    return JsonResponse(
        {
            "message": "Hidrasi berhasil ditambahkan.",
            "amount_ml": hydration_log.amount_ml,
            "target_ml": hydration_log.target_ml,
            "remaining_ml": hydration_log.remaining_ml,
            "progress_percent": hydration_log.progress_percent,
            "target_reached": hydration_log.target_reached,
        }
    )
