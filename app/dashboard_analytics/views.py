import csv
import json

from datetime import date, timedelta

from django.db.models import Count, Sum
from django.contrib.auth import get_user_model

from meal_planner.models import Meal
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST

from .data import IMPACT_SOURCE_COLORS
from .models import (
    HabitEntry,
    ImpactEntry,
    CommunityComment,
    WeeklyBudget,
    WalkingActivity,
)

from habit_tracker.models import (
    Habit,
    HabitLog,
    HydrationLog,
    SleepLog,
    UserStreak,
)


PERIOD_LABELS = {
    "7d": "7 hari",
    "30d": "30 hari",
    "3m": "3 bulan",
    "year": "Tahun ini",
}


HABIT_TARGETS = {
    "water": 2000,
    "steps": 8000,
    "sleep": 480,
    "active": 60,
}


HABIT_LIMITS = {
    "water": 10000,
    "steps": 100000,
    "sleep": 1440,
    "active": 1440,
}


WEEKDAY_NAMES = ("Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min")


MONTH_NAMES = (
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember",
)

WALKING_SPEEDS = {
    "slow": {"label": "Lambat", "kmh": 3.0},
    "normal": {"label": "Normal", "kmh": 4.5},
    "fast": {"label": "Cepat", "kmh": 5.5},
}
WALKING_STEP_LENGTH_METERS = 0.75
MAX_WALKING_DURATION_MINUTES = 1440

def _format_rupiah_number(value):
    return f"{value:,}".replace(",", ".")


def _anonymous_session_key(request):
    """Return a durable guest identifier without combining guest records."""
    if not request.session.session_key:
        request.session.create()

    return request.session.session_key


def _for_request_user(queryset, request):
    """Scope a query to exactly one signed-in user or one guest session."""
    if request.user.is_authenticated:
        return queryset.filter(user=request.user)

    return queryset.filter(
        user__isnull=True,
        anonymous_session_key=_anonymous_session_key(request),
    )


def _entry_owner(request):
    if request.user.is_authenticated:
        return {"user": request.user}

    return {
        "user": None,
        "anonymous_session_key": _anonymous_session_key(request),
    }

def _meal_user(request):
    """Meal Planner bersifat privat; tamu tidak pernah memakai data demo."""
    return request.user if request.user.is_authenticated else None


def _format_number(value):
    return f"{value:,}".replace(",", ".")


def _walking_estimate(duration_minutes, speed_level):
    """Hitung perkiraan dari konstanta Modul 4, bukan dari input klien."""
    speed = WALKING_SPEEDS[speed_level]["kmh"]
    distance_km = speed * duration_minutes / 60
    return {
        "distance_km": round(distance_km, 2),
        "steps": round(distance_km * 1000 / WALKING_STEP_LENGTH_METERS),
    }


def _walking_activity_data(activity):
    estimate = _walking_estimate(activity.duration_minutes, activity.speed_level)
    return {
        "id": activity.pk,
        "duration_minutes": activity.duration_minutes,
        "speed_level": activity.speed_level,
        "speed_label": WALKING_SPEEDS[activity.speed_level]["label"],
        "speed_kmh": WALKING_SPEEDS[activity.speed_level]["kmh"],
        "activity_date": activity.activity_date.isoformat(),
        "distance_km": estimate["distance_km"],
        "steps": estimate["steps"],
    }


def _walking_payload_or_error(payload):
    if payload is None:
        return None, "Format data tidak valid."

    try:
        duration_minutes = int(payload.get("duration_minutes"))
    except (TypeError, ValueError):
        return None, "Durasi berjalan harus berupa bilangan bulat."

    speed_level = payload.get("speed_level")
    if speed_level not in WALKING_SPEEDS:
        return None, "Pilihan kecepatan tidak valid."

    raw_date = payload.get("activity_date")
    try:
        activity_date = date.fromisoformat(raw_date)
    except (TypeError, ValueError):
        return None, "Tanggal aktivitas tidak valid."

    if not 1 <= duration_minutes <= MAX_WALKING_DURATION_MINUTES:
        return None, f"Durasi harus antara 1 dan {MAX_WALKING_DURATION_MINUTES} menit."
    if activity_date > timezone.localdate():
        return None, "Tanggal aktivitas tidak boleh berada di masa depan."

    return {
        "duration_minutes": duration_minutes,
        "speed_level": speed_level,
        "activity_date": activity_date,
    }, None


def _first_day_months_ago(today, months):
    month_index = today.year * 12 + today.month - 1 - months
    year, month_index = divmod(month_index, 12)
    return today.replace(year=year, month=month_index + 1, day=1)


def _selected_period(value):
    return value if value in PERIOD_LABELS else "30d"


def _period_bounds(selected_period, today):
    """Return inclusive dates for a clearly defined analytics period."""
    if selected_period == "7d":
        return today - timedelta(days=6), today

    if selected_period == "30d":
        return today - timedelta(days=29), today

    if selected_period == "3m":
        return _first_day_months_ago(today, 2), today

    return today.replace(month=1, day=1), today


def _previous_period_bounds(period_start, period_end):
    period_length = (period_end - period_start).days + 1
    previous_end = period_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=period_length - 1)
    return previous_start, previous_end



def _habit_week(request, today):
    """Menghitung progres kebiasaan selama 7 hari terakhir."""
    week_start = today - timedelta(days=6)

    empty_week = [
        {
            "label": WEEKDAY_NAMES[(week_start + timedelta(days=i)).weekday()],
            "value": 0,
            "has_data": False,
        }
        for i in range(7)
    ]

    if not request.user.is_authenticated:
        return empty_week, None

    habits = Habit.objects.filter(user=request.user, is_active=True)

    logs = HabitLog.objects.filter(
        habit__in=habits,
        date__range=(week_start, today),
    ).select_related("habit")

    logs_by_day = {}

    for log in logs:
        logs_by_day.setdefault(log.date, []).append(log)

    habit_week = []

    for offset in range(7):
        day = week_start + timedelta(days=offset)

        active_habits = habits.filter(
            created_at__date__lte=day
        ).count()

        day_logs = logs_by_day.get(day, [])

        if active_habits == 0:
            value = 0
            has_data = False
        else:
            completed = sum(
                1 for log in day_logs if log.is_completed
            )
            value = round(completed / active_habits * 100)
            has_data = bool(day_logs)

        habit_week.append({
            "label": WEEKDAY_NAMES[day.weekday()],
            "value": min(value, 100),
            "has_data": has_data,
        })

    values = [
        item["value"]
        for item in habit_week
        if item["has_data"]
    ]

    week_average = (
        round(sum(values) / len(values))
        if values else None
    )

    return habit_week, week_average


def _habit_streak(request):
    """Mengambil streak dari model Habit Tracker."""
    if not request.user.is_authenticated:
        return 0

    streak = UserStreak.objects.filter(
        user=request.user
    ).first()

    return streak.current_streak if streak else 0


def _daily_summary(totals):
    remaining_water = max(
        HABIT_TARGETS["water"] - totals["water"], 0
    )
    remaining_steps = max(
        HABIT_TARGETS["steps"] - totals["steps"], 0
    )

    if not any(totals.values()):
        return "Belum ada kebiasaan yang dicatat hari ini."

    remaining = []

    if remaining_water:
        remaining.append(
            f"{_format_number(remaining_water)} ml air"
        )

    if remaining_steps:
        remaining.append(
            f"{_format_number(remaining_steps)} langkah"
        )

    if not remaining:
        return "Target hidrasi dan langkah hari ini sudah tercapai."

    return f"Sisa target hari ini: {' dan '.join(remaining)}."


def _dashboard_context(request):
    today = timezone.localdate()
    hydration_amount = 0
    hydration_target = 2500
    sleep_minutes = 0
    sleep_target = 450
    activity_title = "Belum ada kebiasaan aktivitas"
    activity_value = 0
    activity_target = 0
    activity_unit = ""
    active_value = 0
    active_target = 0
    active_unit = ""
    active_group_count = 0
    active_has_log = False
    walking_duration = 0
    walking_steps = 0
    habit_list = []

    if request.user.is_authenticated:
        walking_activities = WalkingActivity.objects.filter(
            user=request.user, activity_date=today
        )
        for walking_activity in walking_activities:
            walking_duration += walking_activity.duration_minutes
            walking_steps += _walking_estimate(
                walking_activity.duration_minutes,
                walking_activity.speed_level,
            )["steps"]

        hydration_log = HydrationLog.objects.filter(
            user=request.user, date=today
        ).first()
        if hydration_log:
            hydration_amount = hydration_log.amount_ml
            hydration_target = hydration_log.target_ml

        sleep_log = SleepLog.objects.filter(user=request.user, date=today).first()
        if sleep_log:
            sleep_minutes = sleep_log.duration_minutes
            sleep_target = sleep_log.target_minutes

        active_habits = Habit.objects.filter(user=request.user, is_active=True)
        today_logs = {
            log.habit_id: log
            for log in HabitLog.objects.filter(
                habit__in=active_habits, date=today
            ).select_related("habit")
        }
        activity_habit = active_habits.filter(category="exercise").first()
        if activity_habit:
            activity_log = today_logs.get(activity_habit.id)
            activity_title = activity_habit.title
            activity_value = activity_log.current_value if activity_log else 0
            activity_target = activity_habit.target_value
            activity_unit = activity_habit.unit

        # Satu kartu hanya boleh menjumlahkan olahraga dengan satuan sama.
        # Habit yang telah diarsipkan tetap masuk bila memiliki log hari ini.
        exercise_logs = list(
            HabitLog.objects.filter(
                habit__user=request.user,
                habit__category="exercise",
                date=today,
            ).select_related("habit")
        )
        exercise_habits = {
            habit.id: habit
            for habit in active_habits.filter(category="exercise")
        }
        exercise_habits.update({log.habit_id: log.habit for log in exercise_logs})
        exercise_logs_by_habit = {log.habit_id: log for log in exercise_logs}
        exercise_groups = {}

        for habit in exercise_habits.values():
            unit = habit.unit.strip()
            unit_key = unit.casefold()
            group = exercise_groups.setdefault(
                unit_key,
                {
                    "unit": unit,
                    "value": 0,
                    "target": 0,
                    "has_log": False,
                    "count": 0,
                },
            )
            log = exercise_logs_by_habit.get(habit.id)
            group["value"] += log.current_value if log else 0
            group["target"] += habit.target_value
            group["has_log"] = group["has_log"] or log is not None
            group["count"] += 1

        if exercise_groups:
            logged_groups = [
                (key, group)
                for key, group in exercise_groups.items()
                if group["has_log"]
            ]
            candidate_groups = logged_groups or list(exercise_groups.items())
            active_unit_key, active_group = next(
                (
                    (key, group)
                    for key, group in candidate_groups
                    if key == "menit"
                ),
                candidate_groups[0],
            )
            active_value = active_group["value"]
            active_target = active_group["target"]
            active_unit = active_group["unit"]
            active_group_count = active_group["count"]
            active_has_log = active_group["has_log"]

        for habit in active_habits[:5]:
            log = today_logs.get(habit.id)
            value = log.current_value if log else 0
            percent = min(round(value / habit.target_value * 100), 100)
            habit_list.append({
                "icon": "✓" if log and log.is_completed else "○",
                "title": habit.title,
                "detail": f"{_format_number(value)} dari {_format_number(habit.target_value)} {habit.unit}",
                "complete": bool(log and log.is_completed),
                "progress": percent,
            })

    hydration_progress = min(
        round(hydration_amount / hydration_target * 100), 100
    ) if hydration_target else 0
    sleep_progress = min(round(sleep_minutes / sleep_target * 100), 100) if sleep_target else 0
    activity_progress = min(
        round(activity_value / activity_target * 100), 100
    ) if activity_target else 0
    active_progress = min(
        round(active_value / active_target * 100), 100
    ) if active_target else 0

    recorded_progress = []
    if request.user.is_authenticated:
        if HydrationLog.objects.filter(user=request.user, date=today).exists():
            recorded_progress.append(hydration_progress)
        if SleepLog.objects.filter(user=request.user, date=today).exists():
            recorded_progress.append(sleep_progress)
        if activity_target:
            recorded_progress.append(activity_progress)
    score = round(sum(recorded_progress) / len(recorded_progress)) if recorded_progress else None

    habit_week, week_average = _habit_week(request, today)

    monthly_meal_average = {
        "has_data": False,
        "menu_count": 0,
        "total_cost": 0,
        "average_cost": None,
        "total_cost_display": _format_rupiah_number(0),
        "average_cost_display": None,
    }

    if request.user.is_authenticated:
        monthly_meal_summary = Meal.objects.filter(
            user=request.user,
            date__range=(today.replace(day=1), today),
        ).aggregate(
            menu_count=Count("pk"),
            total_cost=Sum("estimated_cost"),
        )
        monthly_menu_count = monthly_meal_summary["menu_count"] or 0
        monthly_total_cost = monthly_meal_summary["total_cost"] or 0

        if monthly_menu_count:
            monthly_average_cost = round(monthly_total_cost / monthly_menu_count)
            monthly_meal_average = {
                "has_data": True,
                "menu_count": monthly_menu_count,
                "total_cost": monthly_total_cost,
                "average_cost": monthly_average_cost,
                "total_cost_display": _format_rupiah_number(monthly_total_cost),
                "average_cost_display": _format_rupiah_number(monthly_average_cost),
            }

    if request.user.is_authenticated:
        greeting_name = (
            request.user.first_name
            or request.user.get_username()
        )
    else:
        greeting_name = "Pengguna"

    meals = []
    today_cost = 0
    weekly_cost = 0
    if request.user.is_authenticated:
        today_meals = list(Meal.objects.filter(user=request.user, date=today))
        today_cost = sum(meal.estimated_cost for meal in today_meals)
        week_start = today - timedelta(days=today.weekday())
        weekly_cost = (
            Meal.objects.filter(user=request.user, date__range=(week_start, week_start + timedelta(days=6)))
            .aggregate(total=Sum("estimated_cost"))["total"] or 0
        )
        for meal_type, label in Meal.MealType.choices[:3]:
            matching_meals = [meal for meal in today_meals if meal.meal_type == meal_type]
            meals.append({
                "label": label,
                "entries": matching_meals,
                "cost": sum(meal.estimated_cost for meal in matching_meals),
            })
    else:
        meals = [
            {"label": label, "entries": [], "cost": 0}
            for _, label in Meal.MealType.choices[:3]
        ]

    summary = "Belum ada catatan hari ini. Tambahkan melalui Habit Tracker."
    if recorded_progress:
        summary = "Ringkasan diambil dari catatan Habit Tracker hari ini."

    return {
        "date": (
            f"{WEEKDAY_NAMES[today.weekday()]}, "
            f"{today.day} "
            f"{MONTH_NAMES[today.month - 1]} "
            f"{today.year}"
        ),
        "today_iso": today.isoformat(),
        "greeting_name": greeting_name,
        "daily_summary": summary,
        "score": score,
        "score_detail": (
            f"{len(recorded_progress)} indikator resmi tercatat hari ini"
            if recorded_progress
            else "Catat kebiasaan untuk melihat skor"
        ),
        "streak": _habit_streak(request),
        "hydration_ml": hydration_amount,
        "hydration_target": hydration_target,
        "hydration_progress": hydration_progress,
        "hydration_line": f"0,35 100,{35 - hydration_progress * 0.3:.2f}",
        "hydration": {
            "value": f"{hydration_amount / 1000:.1f}".replace(".", ",") + f" / {hydration_target / 1000:g} L",
            "detail": f"{_format_number(hydration_amount)} ml dari target resmi {_format_number(hydration_target)} ml",
            "progress": hydration_progress,
        },
        "sleep": {
            "value": f"{sleep_minutes // 60}j {sleep_minutes % 60:02d}m",
            "detail": f"Target tidur {sleep_target // 60}j {sleep_target % 60:02d}m",
            "progress": sleep_progress,
        },
        "walking": {
            "steps": walking_steps,
            "duration_minutes": walking_duration,
            "value": f"± {_format_number(walking_steps)} langkah",
            "detail": (
                f"Berjalan selama {walking_duration} menit"
                if walking_duration
                else "Belum ada aktivitas berjalan kaki hari ini."
            ),
        },
        "active": {
            "value": f"{_format_number(active_value)} {active_unit}".strip() if active_unit else "0",
            "detail": (
                f"{active_progress}% dari target {_format_number(active_target)} {active_unit}"
                if active_has_log
                else (
                    f"Belum ada log olahraga hari ini • target {_format_number(active_target)} {active_unit}"
                    if active_target
                    else "Belum ada kebiasaan olahraga yang dapat ditampilkan."
                )
            ),
            "progress": active_progress,
            "group_count": active_group_count,
        },
        "habit_week": habit_week,
        "week_average": week_average,
        "habit_list": habit_list,
        "monthly_meal_average": monthly_meal_average,
        "meals": meals,
        "today_meal_cost": today_cost,
        "weekly_meal_cost": weekly_cost,
    }



def _daily_impact_totals(entries):
    return dict(
        entries.values("recorded_on").annotate(total=Sum("packages_avoided")).values_list(
            "recorded_on",
            "total",
        )
    )


def _impact_chart_buckets(selected_period, period_start, period_end, daily_totals):
    buckets = []

    if selected_period == "year":
        for month in range(1, period_end.month + 1):
            month_start = period_end.replace(month=month, day=1)
            next_month = (
                month_start.replace(year=month_start.year + 1, month=1)
                if month == 12
                else month_start.replace(month=month + 1)
            )
            month_end = next_month - timedelta(days=1)
            total = sum(
                amount
                for day, amount in daily_totals.items()
                if month_start <= day <= month_end
            )
            buckets.append({"label": month_start.strftime("%b"), "total": total})

        return buckets

    
    if selected_period == "3m":
        number_of_days = (period_end - period_start).days + 1

        for offset in range(0, number_of_days, 7):
            bucket_start = period_start + timedelta(days=offset)
            bucket_end = min(bucket_start + timedelta(days=6), period_end)
            total = sum(
                amount
                for day, amount in daily_totals.items()
                if bucket_start <= day <= bucket_end
            )

            # Bucket terakhir menggunakan tanggal akhir periode.
            label_date = (
                bucket_end if bucket_end == period_end else bucket_start
            )
            buckets.append({
                "label": label_date.strftime("%d %b"),
                "total": total,
            })

        return buckets


    number_of_days = (period_end - period_start).days + 1

    for offset in range(number_of_days):
        day = period_start + timedelta(days=offset)
        label = WEEKDAY_NAMES[day.weekday()] if selected_period == "7d" else day.strftime("%d %b")
        buckets.append({"label": label, "total": daily_totals.get(day, 0)})

    return buckets


def _period_change_label(current_total, previous_total):
    if previous_total == 0:
        if current_total:
            return "Aktivitas pertama pada periode ini."

        return "Belum ada aktivitas pada periode ini."

    difference = current_total - previous_total

    if difference > 0:
        return f"Naik {difference} kontribusi dari periode sebelumnya."

    if difference < 0:
        return f"Turun {abs(difference)} kontribusi dari periode sebelumnya."

    return "Sama dengan periode sebelumnya."


def _impact_analytics_context(request, selected_period):
    today = timezone.localdate()
    period_start, period_end = _period_bounds(selected_period, today)

    # Anggaran dan biaya makan untuk minggu berjalan (Senin–Minggu).
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    meal_user = _meal_user(request)

    weekly_meals = Meal.objects.filter(
        user=meal_user,
        date__range=(week_start, week_end),
    )

    weekly_cost = (
        weekly_meals.aggregate(total=Sum("estimated_cost"))["total"] or 0
    )

    weekly_budget = None

    if request.user.is_authenticated:
        weekly_budget = WeeklyBudget.objects.filter(
            user=request.user,
            week_start=week_start,
        ).first()

    budget_amount = weekly_budget.amount if weekly_budget else 0

    budget_percent = (
        round(weekly_cost / budget_amount * 100)
        if budget_amount > 0
        else 0
    )

    weekly_budget_data = {
        "week_start": week_start,
        "week_end": week_end,
        "amount": budget_amount,
        "spent": weekly_cost,
        "remaining": max(budget_amount - weekly_cost, 0),
        "percent": budget_percent,
        "progress_width": min(budget_percent, 100),
        "is_over_budget": budget_amount > 0 and weekly_cost > budget_amount,
        "over_budget": max(weekly_cost - budget_amount, 0),
        "has_budget": weekly_budget is not None,
                "amount_display": _format_rupiah_number(budget_amount),
        "spent_display": _format_rupiah_number(weekly_cost),
        "remaining_display": _format_rupiah_number(
            max(budget_amount - weekly_cost, 0)
        ),
        "over_budget_display": _format_rupiah_number(
            max(weekly_cost - budget_amount, 0)
        ),
    }

    # Satu ImpactEntry dan satu Meal tanpa kemasan masing-masing bernilai satu
    # kontribusi. Nilai gabungan bukan jumlah fisik kemasan yang dihindari.
    impact_entries = _for_request_user(ImpactEntry.objects.all(), request).filter(
        recorded_on__range=(period_start, period_end)
    )
    impact_contributions = (
        impact_entries.aggregate(total=Sum("packages_avoided"))["total"] or 0
    )

    # Meal Planner tidak menyimpan status konsumsi atau jumlah kemasan yang
    # dihindari. Setiap Meal dengan nilai eksplisit 0 adalah satu kontribusi
    # menu tanpa kemasan sekali pakai, bukan klaim satu kemasan fisik terhindari.
    if request.user.is_authenticated:
        period_meals = Meal.objects.filter(
            user=request.user,
            date__range=(period_start, period_end),
        )
        homemade_menu_count = period_meals.filter(is_homemade=True).count()
        packaging_free_meals = period_meals.filter(
            packaging_used=0,
        )
        packaging_free_summary = packaging_free_meals.aggregate(
            menu_count=Count("pk"),
            friendly_days=Count("date", distinct=True),
        )
        packaging_free_meal_count = packaging_free_summary["menu_count"] or 0
        friendly_days = packaging_free_summary["friendly_days"] or 0
        meal_daily_totals = dict(
            packaging_free_meals.values("date")
            .annotate(total=Count("pk"))
            .values_list("date", "total")
        )
        meal_type_totals = dict(
            packaging_free_meals.values("meal_type")
            .annotate(total=Count("pk"))
            .values_list("meal_type", "total")
        )
    else:
        homemade_menu_count = 0
        packaging_free_meal_count = 0
        friendly_days = 0
        meal_daily_totals = {}
        meal_type_totals = {}

    contributions = impact_contributions + packaging_free_meal_count

    daily_totals = dict(
        impact_entries.values("recorded_on")
        .annotate(total=Sum("packages_avoided"))
        .values_list("recorded_on", "total")
    )
    for meal_date, meal_total in meal_daily_totals.items():
        daily_totals[meal_date] = daily_totals.get(meal_date, 0) + meal_total

    # Sumber pengurangan mengikuti kategori resmi Meal Planner. ImpactEntry
    # tetap masuk total gabungan, tetapi tidak menentukan kategori menu.
    source_reduction = [
        {
            "label": label,
            "value": meal_type_totals.get(meal_type, 0) or 0,
            "color": IMPACT_SOURCE_COLORS[index % len(IMPACT_SOURCE_COLORS)],
        }
        for index, (meal_type, label) in enumerate(Meal.MealType.choices)
    ]

    most_consistent_source = max(
        source_reduction,
        key=lambda source: source["value"],
        default=None,
    )
    most_consistent_meal_type = (
        most_consistent_source["label"]
        if most_consistent_source and most_consistent_source["value"] > 0
        else "Belum ada data"
    )

    for source in source_reduction:
        source["percent"] = (
            round(source["value"] / packaging_free_meal_count * 100)
            if packaging_free_meal_count
            else 0
        )

    buckets = _impact_chart_buckets(
        selected_period,
        period_start,
        period_end,
        daily_totals,
    )

    trend = []
    trend_labels = []
    running_total = 0

    for bucket in buckets:
        running_total += bucket["total"]
        trend.append(running_total)
        trend_labels.append(bucket["label"])

    chart_max = max(max(trend, default=0), 1)

    chart_points = [
        {
            "label": label,
            "value": value,
            "x": round(index * 100 / max(len(trend) - 1, 1), 2),
            "y": round(95 - value / chart_max * 85, 2),
        }
        for index, (label, value) in enumerate(zip(trend_labels, trend))
    ]

    previous_start, previous_end = _previous_period_bounds(
        period_start,
        period_end,
    )

    previous_impact_contributions = _for_request_user(ImpactEntry.objects.all(), request).filter(
        recorded_on__range=(previous_start, previous_end)
    ).aggregate(total=Sum("packages_avoided"))["total"] or 0

    all_time_impact_contributions = _for_request_user(ImpactEntry.objects.all(), request).aggregate(
        total=Sum("packages_avoided")
    )["total"] or 0

    if request.user.is_authenticated:
        previous_meal_contributions = Meal.objects.filter(
            user=request.user,
            date__range=(previous_start, previous_end),
            packaging_used=0,
        ).count()
        all_time_meal_contributions = Meal.objects.filter(
            user=request.user,
            date__lte=today,
            packaging_used=0,
        ).count()
    else:
        previous_meal_contributions = 0
        all_time_meal_contributions = 0

    previous_contributions = (
        previous_impact_contributions + previous_meal_contributions
    )
    all_time_contributions = (
        all_time_impact_contributions + all_time_meal_contributions
    )

    return {
        "label": PERIOD_LABELS[selected_period],
        "period_start": period_start,
        "period_end": period_end,

        "summary": {
            "contributions": contributions,
            "impact_entries": impact_contributions,
            "homemade_menus": homemade_menu_count,
            "savings": "Belum tersedia",
            "plant_based": "Belum tersedia",
        },

        "weekly_budget": weekly_budget_data,
        "meal_contribution": {
            "count": packaging_free_meal_count,
            "has_records": packaging_free_meal_count > 0,
        },
        "eco_eating": {
            "packaging_free_menus": packaging_free_meal_count,
            "friendly_days": friendly_days,
            "most_consistent_meal_type": most_consistent_meal_type,
        },
        "source_reduction": source_reduction,
        "trend": trend,
        "trend_labels": trend_labels,
        "chart_points": chart_points,
        "change_label": _period_change_label(
            contributions,
            previous_contributions,
        ),
        "has_milestone": all_time_contributions >= 100,
        "all_time_contributions": all_time_contributions,
    }


@login_required(login_url="user_profile:login")
def dashboard(request):
    return render(
        request,
        "dashboard_analytics/dashboard.html",
        {"dashboard": _dashboard_context(request)},
    )


@login_required(login_url="user_profile:login")
def impact_analytics(request):
    selected_period = _selected_period(request.GET.get("period", "30d"))
    analytics = _impact_analytics_context(request, selected_period)

    return render(
        request,
        "dashboard_analytics/impact_analytics.html",
        {
            "analytics": analytics,
            "period_choices": PERIOD_LABELS.items(),
            "selected_period": selected_period,
            "source_reduction": analytics["source_reduction"],
        },
    )


@login_required(login_url="user_profile:login")
@require_GET
def dashboard_data_api(request):
    return JsonResponse({"ok": True, "dashboard": _dashboard_context(request)})


@login_required(login_url="user_profile:login")
def walking_activity_list(request):
    """Halaman daftar aktivitas jalan kaki milik pengguna yang masuk."""
    return render(request, "dashboard_analytics/walking_activities.html")


@login_required(login_url="user_profile:login")
@require_GET
def walking_activities_api(request):
    activities = WalkingActivity.objects.filter(user=request.user)
    return JsonResponse(
        {"ok": True, "activities": [_walking_activity_data(item) for item in activities]}
    )


@login_required(login_url="user_profile:login")
@require_POST
def create_walking_activity(request):
    fields, error = _walking_payload_or_error(_json_payload(request))
    if error:
        return JsonResponse({"ok": False, "message": error}, status=400)

    activity = WalkingActivity.objects.create(user=request.user, **fields)
    return JsonResponse(
        {
            "ok": True,
            "message": "Aktivitas berjalan kaki berhasil disimpan.",
            "activity": _walking_activity_data(activity),
        },
        status=201,
    )


@login_required(login_url="user_profile:login")
@require_POST
def update_walking_activity(request, pk):
    activity = get_object_or_404(WalkingActivity, pk=pk, user=request.user)
    fields, error = _walking_payload_or_error(_json_payload(request))
    if error:
        return JsonResponse({"ok": False, "message": error}, status=400)

    for field, value in fields.items():
        setattr(activity, field, value)
    activity.save(update_fields=[*fields.keys(), "updated_at"])
    return JsonResponse(
        {
            "ok": True,
            "message": "Aktivitas berjalan kaki berhasil diperbarui.",
            "activity": _walking_activity_data(activity),
        }
    )


@login_required(login_url="user_profile:login")
@require_POST
def delete_walking_activity(request, pk):
    activity = get_object_or_404(WalkingActivity, pk=pk, user=request.user)
    activity.delete()
    return JsonResponse({"ok": True, "message": "Aktivitas berjalan kaki berhasil dihapus."})


def _json_payload(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


@login_required(login_url="user_profile:login")
@require_POST
def save_weekly_budget(request):
    """Menyimpan atau memperbarui anggaran makan mingguan pengguna."""

    payload = _json_payload(request)

    if payload is None:
        return JsonResponse(
            {
                "ok": False,
                "message": "Format data tidak valid.",
            },
            status=400,
        )

    try:
        amount = int(payload.get("amount"))
    except (TypeError, ValueError):
        return JsonResponse(
            {
                "ok": False,
                "message": "Nominal anggaran harus berupa angka.",
            },
            status=400,
        )

    if not 1 <= amount <= 100_000_000:
        return JsonResponse(
            {
                "ok": False,
                "message": "Anggaran harus antara Rp1 dan Rp100.000.000.",
            },
            status=400,
        )

    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())

    budget, created = WeeklyBudget.objects.update_or_create(
        user=request.user,
        week_start=week_start,
        defaults={"amount": amount},
    )

    return JsonResponse(
        {
            "ok": True,
            "message": (
                "Anggaran mingguan berhasil disimpan."
                if created
                else "Anggaran mingguan berhasil diperbarui."
            ),
            "budget": {
                "amount": budget.amount,
                "amount_display": _format_number(budget.amount),
                "week_start": budget.week_start.isoformat(),
            },
        },
        status=201 if created else 200,
    )

@login_required(login_url="user_profile:login")
@require_POST
def add_habit_entry(request):
    """Endpoint lama dinonaktifkan agar Modul 4 tidak melewati validasi Modul 3."""
    return JsonResponse(
        {
            "ok": False,
            "message": "Catat kebiasaan melalui Habit Tracker agar validasi dan target resminya digunakan.",
        },
        status=410,
    )


@login_required(login_url="user_profile:login")
@require_POST
def add_impact_entry(request):
    payload = _json_payload(request)

    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Format data tidak valid."},
            status=400,
        )

    activity_type = payload.get("activity_type")
    packages_avoided = payload.get("packages_avoided", 1)
    valid_types = {activity_type for activity_type, _ in ImpactEntry.ACTIVITY_TYPES}

    if activity_type not in valid_types:
        return JsonResponse(
            {"ok": False, "message": "Jenis aktivitas tidak dikenal."},
            status=400,
        )

    try:
        packages_avoided = int(packages_avoided)
    except (TypeError, ValueError):
        return JsonResponse(
            {"ok": False, "message": "Jumlah kemasan harus berupa angka."},
            status=400,
        )

    if not 1 <= packages_avoided <= 1000:
        return JsonResponse(
            {
                "ok": False,
                "message": "Jumlah kemasan harus antara 1 dan 1000.",
            },
            status=400,
        )

    entry = ImpactEntry.objects.create(
        **_entry_owner(request),
        activity_type=activity_type,
        packages_avoided=packages_avoided,
    )

    return JsonResponse(
        {
            "ok": True,
            "message": "Aktivitas pengurangan kemasan berhasil disimpan.",
            "entry": {
                "id": entry.pk,
                "activity_type": entry.activity_type,
                "packages_avoided": entry.packages_avoided,
                "recorded_on": entry.recorded_on.isoformat(),
            },
        },
        status=201,
    )


def _safe_csv_value(value):
    value = str(value)

    return f"'{value}" if value.startswith(("=", "+", "-", "@")) else value


@login_required(login_url="user_profile:login")
@require_GET
def download_report(request):
    selected_period = _selected_period(request.GET.get("period", "30d"))
    analytics = _impact_analytics_context(request, selected_period)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="kosehat-impact-{selected_period}.csv"'
    )
    response.write("\ufeff")
    writer = csv.writer(response)

    writer.writerow(["Rentang", analytics["label"]])
    writer.writerow(
        [
            "Periode",
            f'{analytics["period_start"].isoformat()} s.d. {analytics["period_end"].isoformat()}',
        ]
    )
    writer.writerow([])
    writer.writerow(["Metrik", "Nilai"])
    writer.writerow([
        "Periode anggaran mingguan",
        (
            f'{analytics["weekly_budget"]["week_start"].isoformat()} '
            f's.d. {analytics["weekly_budget"]["week_end"].isoformat()}'
        ),
    ])
    writer.writerow([
        "Kontribusi pengurangan kemasan",
        analytics["summary"]["contributions"],
    ])
    writer.writerow([
        "Kontribusi dari aktivitas pengurangan kemasan (ImpactEntry)",
        analytics["summary"]["impact_entries"],
    ])
    writer.writerow([
        "Menu dengan 0 kemasan sekali pakai tercatat (Meal Planner)",
        analytics["meal_contribution"]["count"],
    ])
    writer.writerow([
        "Konsistensi memasak sendiri (menu)",
        analytics["summary"]["homemade_menus"],
    ])
    writer.writerow([
        "Anggaran mingguan",
        (
            analytics["weekly_budget"]["amount"]
            if analytics["weekly_budget"]["has_budget"]
            else "Belum diatur"
        ),
    ])
    writer.writerow([
        "Biaya makan minggu ini",
        analytics["weekly_budget"]["spent"],
    ])
    writer.writerow([
        "Sisa anggaran",
        (
            analytics["weekly_budget"]["remaining"]
            if analytics["weekly_budget"]["has_budget"]
            else "Belum diatur"
        ),
    ])
    writer.writerow([
        "Persentase anggaran terpakai",
        (
            f'{analytics["weekly_budget"]["percent"]}%'
            if analytics["weekly_budget"]["has_budget"]
            else "Belum diatur"
        ),
    ])
    writer.writerow([
        "Porsi plant-based",
        analytics["summary"]["plant_based"],
    ])
    writer.writerow([
        "Menu tanpa kemasan sekali pakai",
        analytics["eco_eating"]["packaging_free_menus"],
    ])
    writer.writerow([
        "Hari ramah lingkungan",
        analytics["eco_eating"]["friendly_days"],
    ])
    writer.writerow([
        "Kategori makan paling konsisten",
        analytics["eco_eating"]["most_consistent_meal_type"],
    ])
    writer.writerow([])
    writer.writerow(["Sumber kontribusi", "Kontribusi"])

    for source in analytics["source_reduction"]:
        writer.writerow([_safe_csv_value(source["label"]), source["value"]])

    writer.writerow([])
    writer.writerow(["Tren kumulatif", "Kontribusi pengurangan kemasan"])

    for label, value in zip(analytics["trend_labels"], analytics["trend"]):
        writer.writerow([_safe_csv_value(label), value])

    return response


@login_required(login_url="user_profile:login")
@require_GET
def community_comments_api(request):
    """Ambil postingan komunitas beserta balasannya."""
    comments = (
        CommunityComment.objects
        .filter(parent__isnull=True)
        .select_related("user")
        .prefetch_related("replies__user")[:50]
    )

    results = []

    for comment in comments:
        replies = [
            {
                "id": reply.id,
                "content": reply.content,
                "can_delete": (
                    request.user.is_authenticated and reply.user_id == request.user.id
                ),
                "author": (
                    reply.user.get_full_name()
                    or reply.user.get_username()
                    if reply.user
                    else "Pengguna"
                ),
                "created_at": reply.created_at.isoformat(),
            }
            for reply in comment.replies.all().order_by("created_at")
        ]

        results.append({
            "id": comment.id,
            "content": comment.content,
            "can_delete": (
                request.user.is_authenticated and comment.user_id == request.user.id
            ),
            "author": (
                comment.user.get_full_name()
                or comment.user.get_username()
                if comment.user
                else "Pengguna"
            ),
            "created_at": comment.created_at.isoformat(),
            "replies": replies,
        })

    return JsonResponse({"ok": True, "comments": results})


@login_required(login_url="user_profile:login")
@require_POST
def add_community_comment(request):
    """Buat postingan komunitas atau balasan."""
    payload = _json_payload(request)

    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Format data tidak valid."},
            status=400,
        )

    content = payload.get("content")

    if not isinstance(content, str) or not content.strip():
        return JsonResponse(
            {"ok": False, "message": "Komentar tidak boleh kosong."},
            status=400,
        )

    content = content.strip()

    if len(content) > 1000:
        return JsonResponse(
            {"ok": False, "message": "Komentar maksimal 1.000 karakter."},
            status=400,
        )

    parent = None
    parent_id = payload.get("parent_id")

    if parent_id is not None:
        try:
            parent_id = int(parent_id)
            parent = CommunityComment.objects.get(
                pk=parent_id,
                parent__isnull=True,
            )
        except (ValueError, TypeError, CommunityComment.DoesNotExist):
            return JsonResponse(
                {"ok": False, "message": "Postingan yang dibalas tidak ditemukan."},
                status=400,
            )

    comment = CommunityComment.objects.create(
        user=request.user,
        content=content,
        parent=parent,
    )

    author = (
        comment.user.get_full_name()
        or comment.user.get_username()
        if comment.user
        else "Pengguna Demo"
    )

    return JsonResponse(
        {
            "ok": True,
            "message": "Komentar berhasil dikirim.",
            "comment": {
                "id": comment.id,
                "content": comment.content,
                "author": author,
                "created_at": comment.created_at.isoformat(),
                "parent_id": comment.parent_id,
            },
        },
        status=201,
    )


@login_required(login_url="user_profile:login")
@require_POST
def delete_community_comment(request, pk):
    """Hapus komentar atau balasan milik pengguna yang sedang masuk."""
    # Filter pemilik dilakukan di backend; ID saja tidak cukup untuk menghapus.
    comment = get_object_or_404(CommunityComment, pk=pk, user=request.user)
    parent_id = comment.parent_id
    comment.delete()

    return JsonResponse(
        {
            "ok": True,
            "message": "Komentar berhasil dihapus.",
            "deleted_id": pk,
            "parent_id": parent_id,
        }
    )
