import csv
import json

from datetime import timedelta

from django.db.models import Count, Sum
from django.contrib.auth import get_user_model

from app.meal_planner.models import Meal
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .data import IMPACT_SOURCE_COLORS, IMPACT_TARGETS
from .models import HabitEntry, ImpactEntry, CommunityComment


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
    """Gunakan akun yang sama dengan Meal Planner."""
    if request.user.is_authenticated:
        return request.user

    user, _ = get_user_model().objects.get_or_create(
        username="demo"
    )
    return user


def _format_number(value):
    return f"{value:,}".replace(",", ".")


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


def _habit_totals(entries):
    totals = {habit_type: 0 for habit_type in HABIT_TARGETS}

    for row in entries.values("habit_type").annotate(total=Sum("amount")):
        totals[row["habit_type"]] = row["total"] or 0

    return totals


def _hydration_chart(entries, total_water):
    points = ["0,35"]
    cumulative_water = 0
    maximum_water = max(HABIT_TARGETS["water"], total_water)

    for entry in entries.filter(habit_type="water").order_by("created_at"):
        cumulative_water += entry.amount
        local_time = timezone.localtime(entry.created_at)
        x = (local_time.hour + local_time.minute / 60) / 24 * 100
        y = 35 - cumulative_water / maximum_water * 30
        points.append(f"{x:.2f},{y:.2f}")

    final_y = 35 - total_water / maximum_water * 30 if total_water else 35
    points.append(f"100,{final_y:.2f}")

    return " ".join(points)


def _habit_week(request, today):
    week_start = today - timedelta(days=6)
    rows = _for_request_user(HabitEntry.objects.all(), request).filter(
        recorded_on__range=(week_start, today)
    ).values("recorded_on", "habit_type").annotate(total=Sum("amount"))

    totals_by_day = {
        week_start + timedelta(days=offset): {
            habit_type: 0 for habit_type in HABIT_TARGETS
        }
        for offset in range(7)
    }
    recorded_types_by_day = {day: set() for day in totals_by_day}

    for row in rows:
        day = row["recorded_on"]
        habit_type = row["habit_type"]
        totals_by_day[day][habit_type] = row["total"] or 0
        recorded_types_by_day[day].add(habit_type)

    habit_week = []

    for day, totals in totals_by_day.items():
        progresses = [
            min(round(totals[habit_type] / HABIT_TARGETS[habit_type] * 100), 100)
            for habit_type in recorded_types_by_day[day]
        ]
        has_data = bool(progresses)

        habit_week.append(
            {
                "label": WEEKDAY_NAMES[day.weekday()],
                "value": round(sum(progresses) / len(progresses)) if has_data else 0,
                "has_data": has_data,
            }
        )

    values = [day["value"] for day in habit_week if day["has_data"]]
    week_average = round(sum(values) / len(values)) if values else None

    return habit_week, week_average


def _habit_streak(request, today):
    recorded_days = set(
        _for_request_user(HabitEntry.objects.all(), request).filter(
            recorded_on__lte=today
        ).values_list("recorded_on", flat=True).distinct()
    )
    streak = 0
    day = today

    while day in recorded_days:
        streak += 1
        day -= timedelta(days=1)

    return streak


def _daily_summary(totals):
    remaining_water = max(HABIT_TARGETS["water"] - totals["water"], 0)
    remaining_steps = max(HABIT_TARGETS["steps"] - totals["steps"], 0)

    if not any(totals.values()):
        return "Belum ada kebiasaan yang dicatat hari ini."

    remaining = []

    if remaining_water:
        remaining.append(f"{_format_number(remaining_water)} ml air")

    if remaining_steps:
        remaining.append(f"{_format_number(remaining_steps)} langkah")

    if not remaining:
        return "Target hidrasi dan langkah hari ini sudah tercapai."

    return f"Sisa target hari ini: {' dan '.join(remaining)}."


def _dashboard_context(request):
    today = timezone.localdate()
    today_entries = _for_request_user(HabitEntry.objects.all(), request).filter(
        recorded_on=today
    )
    totals = _habit_totals(today_entries)
    progress = {
        habit_type: min(round(totals[habit_type] / target * 100), 100)
        for habit_type, target in HABIT_TARGETS.items()
    }
    recorded_types = set(
        today_entries.values_list("habit_type", flat=True).distinct()
    )
    score_values = [progress[habit_type] for habit_type in recorded_types]
    score = round(sum(score_values) / len(score_values)) if score_values else None
    habit_week, week_average = _habit_week(request, today)
    month_impact_entries = _for_request_user(ImpactEntry.objects.all(), request).filter(
        recorded_on__range=(today.replace(day=1), today)
    )
    month_impact = month_impact_entries.aggregate(total=Sum("packages_avoided"))["total"] or 0

    if request.user.is_authenticated:
        greeting_name = request.user.first_name or request.user.get_username()
    else:
        greeting_name = "Pengguna"

    water = totals["water"]
    sleep = totals["sleep"]
    steps = totals["steps"]
    active = totals["active"]

    return {
        "date": f"{WEEKDAY_NAMES[today.weekday()]}, {today.day} {MONTH_NAMES[today.month - 1]} {today.year}",
        "greeting_name": greeting_name,
        "daily_summary": _daily_summary(totals),
        "score": score,
        "score_detail": (
            f"{len(score_values)} dari 4 indikator dicatat hari ini"
            if score_values
            else "Catat kebiasaan untuk melihat skor"
        ),
        "streak": _habit_streak(request, today),
        "hydration_ml": water,
        "hydration_progress": progress["water"],
        "hydration_line": _hydration_chart(today_entries, water),
        "hydration": {
            "value": f"{water / 1000:.1f}".replace(".", ",") + " / 2 L",
            "detail": f"{_format_number(water)} ml tercatat hari ini",
            "progress": progress["water"],
        },
        "sleep": {
            "value": f"{sleep // 60}j {sleep % 60:02d}m",
            "detail": "Durasi tidur yang kamu catat hari ini",
            "progress": progress["sleep"],
        },
        "steps": {
            "value": _format_number(steps),
            "detail": f"{progress['steps']}% dari target 8.000 langkah",
            "progress": progress["steps"],
        },
        "active": {
            "value": f"{active} mnt",
            "detail": "Menit gerak aktif tercatat hari ini",
            "progress": progress["active"],
        },
        "habit_week": habit_week,
        "week_average": week_average,
        "habit_list": [
            {
                "icon": "♧",
                "title": "Minum 2 liter",
                "detail": f"{_format_number(water)} ml dari target 2.000 ml",
                "complete": water >= HABIT_TARGETS["water"],
            },
            {
                "icon": "☾",
                "title": "Durasi tidur 8 jam",
                "detail": f"{sleep // 60}j {sleep % 60:02d}m dari target 8 jam",
                "complete": sleep >= HABIT_TARGETS["sleep"],
            },
            {
                "icon": "♧",
                "title": "Jalan 8.000 langkah",
                "detail": f"{_format_number(steps)} langkah dari target 8.000",
                "complete": steps >= HABIT_TARGETS["steps"],
            },
        ],
        "month_impact": month_impact,
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
        return f"Naik {difference} item dari periode sebelumnya."

    if difference < 0:
        return f"Turun {abs(difference)} item dari periode sebelumnya."

    return "Sama dengan periode sebelumnya."


def _impact_analytics_context(request, selected_period):
    today = timezone.localdate()
    period_start, period_end = _period_bounds(selected_period, today)

    # Sumber data sekarang berasal dari Meal Planner.
    meal_entries = Meal.objects.filter(
        user=_meal_user(request),
        date__range=(period_start, period_end),
        packaging_used=0,
    )

    # Asumsi prototipe: satu menu tanpa kemasan = estimasi
    # satu kemasan sekali pakai yang dihindari.
    packages = meal_entries.count()

    # Jumlah estimasi kemasan dihindari per tanggal.
    daily_totals = dict(
        meal_entries.values("date")
        .annotate(total=Count("id"))
        .values_list("date", "total")
    )

    # Kontribusi berdasarkan jenis makanan di Meal Planner.
    source_totals = dict(
        meal_entries.values("meal_type")
        .annotate(total=Count("id"))
        .values_list("meal_type", "total")
    )

    meal_types = list(Meal.MealType.choices)
    source_reduction = [
        {
            "label": label,
            "value": source_totals.get(meal_type, 0) or 0,
            "color": IMPACT_SOURCE_COLORS[index % len(IMPACT_SOURCE_COLORS)],
        }
        for index, (meal_type, label) in enumerate(meal_types)
    ]

    largest_source = max(
        (source["value"] for source in source_reduction),
        default=0,
    )

    for source in source_reduction:
        source["percent"] = (
            round(source["value"] / largest_source * 100)
            if largest_source
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

    target = IMPACT_TARGETS[selected_period]
    chart_max = max(max(trend, default=0), target, 1)

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

    previous_packages = Meal.objects.filter(
        user=_meal_user(request),
        date__range=(previous_start, previous_end),
        packaging_used=0,
    ).count()

    all_time_packages = Meal.objects.filter(
        user=_meal_user(request),
        packaging_used=0,
    ).count()

    return {
        "label": PERIOD_LABELS[selected_period],
        "period_start": period_start,
        "period_end": period_end,
        "summary": {
            "packages": packages,
            "emissions": "Belum tersedia",
            "savings": "Belum tersedia",
            "plant_based": "Belum tersedia",
        },
        "source_reduction": source_reduction,
        "trend": trend,
        "trend_labels": trend_labels,
        "target": target,
        "chart_points": chart_points,
        "percent": min(round(packages / target * 100), 100),
        "remaining": max(target - packages, 0),
        "change_label": _period_change_label(
            packages,
            previous_packages,
        ),
        "has_milestone": all_time_packages >= 100,
        "all_time_packages": all_time_packages,
    }


def dashboard(request):
    return render(
        request,
        "dashboard_analytics/dashboard.html",
        {"dashboard": _dashboard_context(request)},
    )


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


@require_GET
def dashboard_data_api(request):
    return JsonResponse({"ok": True, "dashboard": _dashboard_context(request)})


def _json_payload(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


@require_POST
def add_habit_entry(request):
    payload = _json_payload(request)

    if payload is None:
        return JsonResponse(
            {"ok": False, "message": "Format data tidak valid."},
            status=400,
        )

    habit_type = payload.get("habit_type")
    amount = payload.get("amount")

    if habit_type not in HABIT_LIMITS:
        return JsonResponse(
            {"ok": False, "message": "Jenis kebiasaan tidak dikenal."},
            status=400,
        )

    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return JsonResponse(
            {"ok": False, "message": "Masukkan angka yang valid."},
            status=400,
        )

    if not 0 < amount <= HABIT_LIMITS[habit_type]:
        return JsonResponse(
            {
                "ok": False,
                "message": "Nilai harus lebih besar dari 0 dan masih masuk akal.",
            },
            status=400,
        )

    entry = HabitEntry.objects.create(
        **_entry_owner(request),
        habit_type=habit_type,
        amount=amount,
    )

    return JsonResponse(
        {
            "ok": True,
            "message": "Catatan kebiasaan berhasil disimpan.",
            "entry": {
                "id": entry.pk,
                "habit_type": entry.habit_type,
                "amount": entry.amount,
                "recorded_on": entry.recorded_on.isoformat(),
            },
        },
        status=201,
    )


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
    writer.writerow(["Estimasi kemasan dihindari (item)", analytics["summary"]["packages"]])
    writer.writerow(["Emisi dihemat", analytics["summary"]["emissions"]])
    writer.writerow(["Uang dihemat", analytics["summary"]["savings"]])
    writer.writerow(["Porsi plant-based", analytics["summary"]["plant_based"]])
    writer.writerow([])
    writer.writerow(["Sumber pengurangan","Estimasi kemasan dihindari (item)"])

    for source in analytics["source_reduction"]:
        writer.writerow([_safe_csv_value(source["label"]), source["value"]])

    writer.writerow([])
    writer.writerow(["Tren kumulatif", "Estimasi kemasan dihindari"])

    for label, value in zip(analytics["trend_labels"], analytics["trend"]):
        writer.writerow([_safe_csv_value(label), value])

    return response


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
        user=request.user if request.user.is_authenticated else None,
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
