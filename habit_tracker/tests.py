from datetime import datetime, time, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from habit_tracker.models import (
    EnergyLog,
    Habit,
    HabitLog,
    HydrationLog,
    SleepLog,
    UserStreak,
)


class HabitTrackerTestMixin:
    def create_habit(self, title="Minum Air", target=1, unit="kali"):
        return Habit.objects.create(
            user=self.user,
            title=title,
            category="water",
            target_value=target,
            unit=unit,
        )

    def url(self, name, *args):
        return reverse(f"habit_tracker:{name}", args=args)


class HabitModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="model-user",
            password="password123",
        )
        self.habit = Habit.objects.create(
            user=self.user,
            title="Jalan kaki",
            target_value=8000,
            unit="langkah",
        )

    def test_habit_string_and_archive(self):
        self.assertEqual(str(self.habit), "Jalan kaki - model-user")
        self.habit.archive()
        self.habit.refresh_from_db()
        self.assertFalse(self.habit.is_active)
        self.assertIsNotNone(self.habit.archived_at)

    def test_habit_log_progress_is_capped_and_completed(self):
        log = HabitLog.objects.create(
            habit=self.habit,
            date=timezone.localdate(),
            current_value=10000,
        )
        self.assertEqual(log.current_value, 8000)
        self.assertTrue(log.is_completed)
        self.assertEqual(log.progress_percent, 100)
        self.assertIsNotNone(log.logged_time)

    def test_habit_log_partial_progress(self):
        log = HabitLog.objects.create(
            habit=self.habit,
            date=timezone.localdate(),
            current_value=4000,
        )
        self.assertFalse(log.is_completed)
        self.assertEqual(log.progress_percent, 50)

    def test_sleep_status(self):
        sleep = SleepLog.objects.create(
            user=self.user,
            date=timezone.localdate(),
            duration_minutes=400,
            target_hours=7.5,
        )
        self.assertEqual(sleep.target_minutes, 450)
        self.assertEqual(sleep.sleep_status, "kurang")
        sleep.duration_minutes = 480
        sleep.save()
        self.assertEqual(sleep.sleep_status, "sesuai")

    def test_energy_target_reached(self):
        energy = EnergyLog.objects.create(
            user=self.user,
            date=timezone.localdate(),
            focus_minutes=180,
            logged_focus_minutes=180,
        )
        self.assertTrue(energy.focus_target_reached)
        self.assertIn("model-user", str(energy))

    def test_hydration_properties(self):
        hydration = HydrationLog.objects.create(
            user=self.user,
            date=timezone.localdate(),
            amount_ml=1250,
        )
        self.assertEqual(hydration.target_ml, 2500)
        self.assertEqual(hydration.remaining_ml, 1250)
        self.assertEqual(hydration.progress_percent, 50)
        self.assertFalse(hydration.target_reached)
        hydration.amount_ml = 2500
        hydration.save()
        self.assertTrue(hydration.target_reached)

    def test_user_streak_string(self):
        streak = UserStreak.objects.create(
            user=self.user,
            current_streak=2,
            best_streak=5,
        )
        self.assertIn("Streak: 2", str(streak))


class HabitTrackerEndpointTests(HabitTrackerTestMixin, TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="ranu",
            password="password123",
        )
        self.other_user = User.objects.create_user(
            username="other",
            password="password123",
        )
        self.client.login(username="ranu", password="password123")
        self.habit = self.create_habit()

    def test_tracker_page_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url("index")).status_code, 302)

    def test_tracker_page_loads(self):
        self.assertEqual(self.client.get(self.url("index")).status_code, 200)

    def test_get_habits_creates_daily_defaults(self):
        response = self.client.get(self.url("get_habits"))
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["summary"]["total"], 1)
        self.assertEqual(data["summary"]["completed"], 0)
        self.assertEqual(data["summary"]["progress_percent"], 0)
        self.assertEqual(data["summary"]["target_focus_minutes"], 180)
        self.assertEqual(data["summary"]["logged_focus_minutes"], 0)
        self.assertEqual(data["summary"]["hydration"]["amount_ml"], 0)
        self.assertEqual(data["summary"]["hydration"]["target_ml"], 2500)
        self.assertEqual(data["summary"]["sleep"]["last_night_str"], "0m")
        self.assertEqual(len(data["summary"]["weekly_consistency"]), 7)

    def test_add_habit_valid_and_invalid(self):
        response = self.client.post(
            self.url("add_habit"),
            {
                "title": "Olahraga Pagi",
                "category": "exercise",
                "target_value": 15,
                "unit": "menit",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Habit.objects.filter(user=self.user).count(), 2)
        invalid = self.client.post(
            self.url("add_habit"),
            {"title": "", "category": "exercise", "target_value": 0, "unit": "menit"},
        )
        self.assertEqual(invalid.status_code, 400)

    def test_toggle_habit(self):
        response = self.client.post(self.url("toggle_habit", self.habit.id))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_completed"])
        response = self.client.post(self.url("toggle_habit", self.habit.id))
        self.assertFalse(response.json()["is_completed"])

    def test_partial_habit_progress(self):
        self.habit.target_value = 10
        self.habit.save()
        response = self.client.post(
            self.url("add_habit_progress", self.habit.id),
            {"additional_value": 4},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["current_value"], 4)
        self.assertEqual(response.json()["progress_percent"], 40)
        invalid = self.client.post(
            self.url("add_habit_progress", self.habit.id),
            {"additional_value": 0},
        )
        self.assertEqual(invalid.status_code, 400)

    def test_archive_habit_and_protect_other_user_data(self):
        other_habit = Habit.objects.create(user=self.other_user, title="Other")
        response = self.client.post(self.url("delete_habit", other_habit.id))
        self.assertEqual(response.status_code, 404)
        response = self.client.post(self.url("delete_habit", self.habit.id))
        self.assertEqual(response.status_code, 200)
        self.habit.refresh_from_db()
        self.assertFalse(self.habit.is_active)

    def test_focus_settings_and_add_session(self):
        response = self.client.post(self.url("log_energy"), {"focus_minutes": 210})
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            self.url("add_focus_time"),
            {"additional_minutes": 60},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["logged_focus_minutes"], 60)
        self.assertFalse(response.json()["is_target_reached"])
        invalid = self.client.post(
            self.url("add_focus_time"),
            {"additional_minutes": 0},
        )
        self.assertEqual(invalid.status_code, 400)

    def test_sleep_settings(self):
        response = self.client.post(
            self.url("log_sleep_settings"),
            {"target_hours": 7.5, "sleep_hours": 7, "sleep_minutes": 30},
        )
        self.assertEqual(response.status_code, 200)
        sleep = SleepLog.objects.get(user=self.user, date=timezone.localdate())
        self.assertEqual(sleep.duration_minutes, 450)
        self.assertEqual(response.json()["status"], "sesuai")

    def test_hydration_adds_to_daily_total(self):
        response = self.client.post(self.url("add_hydration"), {"amount_ml": 500})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["amount_ml"], 500)
        self.assertEqual(response.json()["target_ml"], 2500)
        response = self.client.post(self.url("add_hydration"), {"amount_ml": 2000})
        self.assertTrue(response.json()["target_reached"])

    def test_api_methods_and_invalid_habit_id(self):
        self.assertEqual(self.client.post(self.url("get_habits")).status_code, 405)
        self.assertEqual(
            self.client.post(self.url("toggle_habit", 99999)).status_code,
            404,
        )


class StreakAndDailyResetTests(HabitTrackerTestMixin, TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="streak-user",
            password="password123",
        )
        self.client.login(username="streak-user", password="password123")
        self.habit = self.create_habit("Kebiasaan harian")
        yesterday = timezone.localdate() - timedelta(days=1)
        Habit.objects.filter(pk=self.habit.pk).update(
            created_at=timezone.make_aware(
                datetime.combine(yesterday - timedelta(days=1), time.min)
            )
        )

    def test_streak_increments_when_previous_day_is_complete(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        HabitLog.objects.create(habit=self.habit, date=yesterday, current_value=1)
        UserStreak.objects.create(user=self.user, last_checked_date=yesterday)
        summary = self.client.get(self.url("get_habits")).json()["summary"]
        self.assertEqual(summary["streak"], 1)
        self.assertEqual(summary["best_streak"], 1)

    def test_streak_resets_when_previous_day_is_incomplete(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        HabitLog.objects.create(habit=self.habit, date=yesterday, current_value=0)
        UserStreak.objects.create(
            user=self.user,
            current_streak=3,
            best_streak=5,
            last_checked_date=yesterday,
        )
        summary = self.client.get(self.url("get_habits")).json()["summary"]
        self.assertEqual(summary["streak"], 0)
        self.assertEqual(summary["best_streak"], 5)

    def test_new_day_has_zero_habit_progress(self):
        HabitLog.objects.create(
            habit=self.habit,
            date=timezone.localdate() - timedelta(days=1),
            current_value=1,
        )
        data = self.client.get(self.url("get_habits")).json()
        self.assertEqual(data["summary"]["completed"], 0)
        self.assertEqual(data["summary"]["progress_percent"], 0)
        self.assertEqual(data["habits"][0]["current_value"], 0)
