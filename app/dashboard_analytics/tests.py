import json
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from habit_tracker.models import EnergyLog, Habit, HabitLog, HydrationLog, SleepLog
from meal_planner.models import Meal
from recipe_catalog.models import Recipe

from .models import CommunityComment, ImpactEntry, WalkingActivity, WeeklyBudget


class DashboardAnalyticsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="prajna", password="test-password", first_name="Prajna"
        )
        self.other_user = get_user_model().objects.create_user(
            username="teman", password="test-password"
        )
        self.client.force_login(self.user)

    def test_dashboard_reads_only_current_users_module_two_and_three_data(self):
        today = timezone.localdate()
        HydrationLog.objects.create(user=self.user, date=today, amount_ml=1250, target_ml=2500)
        SleepLog.objects.create(user=self.user, date=today, duration_minutes=420, target_hours=7.5)
        EnergyLog.objects.create(user=self.user, date=today, focus_minutes=180, logged_focus_minutes=90)
        habit = Habit.objects.create(
            user=self.user, title="Jalan kaki", category="exercise", target_value=8000, unit="langkah"
        )
        HabitLog.objects.create(habit=habit, date=today, current_value=4000)
        Meal.objects.create(
            user=self.user, date=today, meal_type=Meal.MealType.SARAPAN,
            name="Nasi telur", estimated_cost=12000
        )
        Meal.objects.create(
            user=self.other_user, date=today, meal_type=Meal.MealType.SARAPAN,
            name="Menu privat", estimated_cost=99000
        )

        response = self.client.get(reverse("dashboard_analytics:dashboard"))
        dashboard = response.context["dashboard"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(dashboard["hydration_ml"], 1250)
        self.assertEqual(dashboard["hydration_target"], 2500)
        self.assertEqual(dashboard["sleep"]["value"], "7j 00m")
        self.assertEqual(dashboard["active"]["value"], "4.000 langkah")
        self.assertEqual(dashboard["active"]["detail"], "50% dari target 8.000 langkah")
        self.assertNotIn("Fokus", dashboard["active"]["detail"])
        self.assertEqual(dashboard["meals"][0]["entries"][0].name, "Nasi telur")
        self.assertEqual(dashboard["today_meal_cost"], 12000)

    def test_dashboard_monthly_average_meal_cost_uses_all_current_user_meals(self):
        today = timezone.localdate()
        Meal.objects.create(
            user=self.user,
            date=today,
            meal_type=Meal.MealType.SARAPAN,
            name="Sarapan homemade",
            estimated_cost=10000,
            is_homemade=True,
        )
        Meal.objects.create(
            user=self.user,
            date=today - timedelta(days=1),
            meal_type=Meal.MealType.SIANG,
            name="Makan siang beli",
            estimated_cost=20000,
            is_homemade=False,
        )
        Meal.objects.create(
            user=self.user,
            date=today.replace(day=1) - timedelta(days=1),
            meal_type=Meal.MealType.MALAM,
            name="Menu bulan lalu",
            estimated_cost=90000,
        )
        Meal.objects.create(
            user=self.other_user,
            date=today,
            meal_type=Meal.MealType.CAMILAN,
            name="Menu privat",
            estimated_cost=99000,
        )

        response = self.client.get(reverse("dashboard_analytics:dashboard"))
        average = response.context["dashboard"]["monthly_meal_average"]

        self.assertTrue(average["has_data"])
        self.assertEqual(average["menu_count"], 2)
        self.assertEqual(average["total_cost"], 30000)
        self.assertEqual(average["average_cost"], 15000)
        self.assertEqual(average["average_cost_display"], "15.000")
        self.assertContains(response, "Rata-rata Biaya per Menu")
        self.assertNotContains(response, "Dampak bulan ini")

    def test_dashboard_monthly_average_meal_cost_has_honest_empty_state(self):
        response = self.client.get(reverse("dashboard_analytics:dashboard"))
        average = response.context["dashboard"]["monthly_meal_average"]

        self.assertFalse(average["has_data"])
        self.assertEqual(average["menu_count"], 0)
        self.assertIsNone(average["average_cost"])
        self.assertContains(response, "Belum ada data")

    def test_dashboard_and_impact_use_standard_contextual_emoji(self):
        dashboard_response = self.client.get(reverse("dashboard_analytics:dashboard"))
        impact_response = self.client.get(reverse("dashboard_analytics:impact_analytics"))
        walking_response = self.client.get(reverse("dashboard_analytics:walking_activity_list"))

        for emoji in ("🔔", "🔥", "💧", "👣", "⚡️"):
            self.assertContains(dashboard_response, emoji)
        for emoji in ("🔔", "🌱"):
            self.assertContains(impact_response, emoji)
        self.assertContains(walking_response, "👣 Catatan berjalan kaki")
        self.assertNotContains(dashboard_response, "♧")
        self.assertNotContains(dashboard_response, "♨")
        self.assertNotContains(impact_response, "♧")
        self.assertNotContains(impact_response, "✦")

    def test_active_card_aggregates_exercise_habits_with_the_same_unit(self):
        today = timezone.localdate()
        jogging = Habit.objects.create(
            user=self.user, title="Jogging", category="exercise", target_value=30, unit="menit"
        )
        yoga = Habit.objects.create(
            user=self.user, title="Yoga", category="exercise", target_value=20, unit="menit"
        )
        HabitLog.objects.create(habit=jogging, date=today, current_value=20)
        HabitLog.objects.create(habit=yoga, date=today, current_value=15)

        active = self.client.get(reverse("dashboard_analytics:dashboard")).context["dashboard"]["active"]

        self.assertEqual(active["value"], "35 menit")
        self.assertEqual(active["detail"], "70% dari target 50 menit")
        self.assertEqual(active["progress"], 70)
        self.assertEqual(active["group_count"], 2)

    def test_active_card_does_not_mix_exercise_units_or_other_users_data(self):
        today = timezone.localdate()
        jogging = Habit.objects.create(
            user=self.user, title="Jogging", category="exercise", target_value=30, unit="menit"
        )
        cycling = Habit.objects.create(
            user=self.user, title="Bersepeda", category="exercise", target_value=5, unit="km"
        )
        other_jogging = Habit.objects.create(
            user=self.other_user, title="Jogging teman", category="exercise", target_value=60, unit="menit"
        )
        HabitLog.objects.create(habit=jogging, date=today, current_value=20)
        HabitLog.objects.create(habit=cycling, date=today, current_value=3)
        HabitLog.objects.create(habit=other_jogging, date=today, current_value=60)

        active = self.client.get(reverse("dashboard_analytics:dashboard")).context["dashboard"]["active"]

        self.assertEqual(active["value"], "20 menit")
        self.assertEqual(active["detail"], "67% dari target 30 menit")
        self.assertNotIn("km", active["value"])
        self.assertNotIn("80", active["value"])

    def test_active_card_is_zero_without_exercise_log_and_ignores_energy_log(self):
        today = timezone.localdate()
        Habit.objects.create(
            user=self.user, title="Yoga", category="exercise", target_value=20, unit="menit"
        )
        EnergyLog.objects.create(
            user=self.user, date=today, focus_minutes=180, logged_focus_minutes=175
        )

        active = self.client.get(reverse("dashboard_analytics:dashboard")).context["dashboard"]["active"]

        self.assertEqual(active["value"], "0 menit")
        self.assertEqual(active["progress"], 0)
        self.assertIn("Belum ada log olahraga hari ini", active["detail"])
        self.assertNotIn("175", active["detail"])

    def test_walking_activity_create_uses_official_speed_constants(self):
        url = reverse("dashboard_analytics:create_walking_activity")
        today = timezone.localdate().isoformat()
        cases = (
            ("slow", 30, 1.5, 2000),
            ("normal", 30, 2.25, 3000),
            ("fast", 30, 2.75, 3667),
        )

        for speed_level, duration, distance, steps in cases:
            response = self.client.post(
                url,
                data=json.dumps({
                    "duration_minutes": duration,
                    "speed_level": speed_level,
                    "activity_date": today,
                }),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["activity"]["distance_km"], distance)
            self.assertEqual(response.json()["activity"]["steps"], steps)

        self.assertEqual(WalkingActivity.objects.filter(user=self.user).count(), 3)

    def test_walking_dashboard_aggregates_each_record_estimate(self):
        today = timezone.localdate()
        WalkingActivity.objects.create(
            user=self.user, activity_date=today, duration_minutes=15, speed_level="normal"
        )
        WalkingActivity.objects.create(
            user=self.user, activity_date=today, duration_minutes=20, speed_level="slow"
        )
        WalkingActivity.objects.create(
            user=self.other_user, activity_date=today, duration_minutes=60, speed_level="fast"
        )

        walking = self.client.get(reverse("dashboard_analytics:dashboard")).context["dashboard"]["walking"]

        self.assertEqual(walking["duration_minutes"], 35)
        self.assertEqual(walking["steps"], 2833)
        self.assertEqual(walking["value"], "± 2.833 langkah")
        self.assertEqual(walking["detail"], "Berjalan selama 35 menit")

    def test_walking_activity_update_delete_and_owner_isolation(self):
        activity = WalkingActivity.objects.create(
            user=self.user, activity_date=timezone.localdate(), duration_minutes=10, speed_level="slow"
        )
        other_activity = WalkingActivity.objects.create(
            user=self.other_user, activity_date=timezone.localdate(), duration_minutes=10, speed_level="slow"
        )
        update_url = reverse("dashboard_analytics:update_walking_activity", args=[activity.pk])
        response = self.client.post(
            update_url,
            data=json.dumps({
                "duration_minutes": 30,
                "speed_level": "fast",
                "activity_date": timezone.localdate().isoformat(),
            }),
            content_type="application/json",
        )
        activity.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(activity.duration_minutes, 30)
        self.assertEqual(activity.speed_level, "fast")
        self.assertEqual(response.json()["activity"]["steps"], 3667)
        self.assertEqual(
            self.client.post(
                reverse("dashboard_analytics:update_walking_activity", args=[other_activity.pk]),
                data=json.dumps({"duration_minutes": 20, "speed_level": "normal", "activity_date": timezone.localdate().isoformat()}),
                content_type="application/json",
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(reverse("dashboard_analytics:delete_walking_activity", args=[activity.pk])).status_code,
            200,
        )
        self.assertFalse(WalkingActivity.objects.filter(pk=activity.pk).exists())
        self.assertTrue(WalkingActivity.objects.filter(pk=other_activity.pk).exists())

    def test_walking_activity_list_is_private_and_newest_first(self):
        older = WalkingActivity.objects.create(
            user=self.user,
            activity_date=timezone.localdate() - timedelta(days=1),
            duration_minutes=10,
            speed_level="slow",
        )
        newer = WalkingActivity.objects.create(
            user=self.user,
            activity_date=timezone.localdate(),
            duration_minutes=20,
            speed_level="normal",
        )
        WalkingActivity.objects.create(
            user=self.other_user,
            activity_date=timezone.localdate(),
            duration_minutes=30,
            speed_level="fast",
        )

        response = self.client.get(reverse("dashboard_analytics:walking_activities_api"))
        activities = response.json()["activities"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in activities], [newer.pk, older.pk])
        self.assertEqual(
            Client().get(reverse("dashboard_analytics:walking_activities_api")).status_code,
            302,
        )

    def test_walking_activity_rejects_invalid_or_future_input_and_empty_dashboard_is_zero(self):
        today = timezone.localdate()
        walking = self.client.get(reverse("dashboard_analytics:dashboard")).context["dashboard"]["walking"]
        self.assertEqual(walking["value"], "± 0 langkah")
        self.assertIn("Belum ada aktivitas", walking["detail"])

        url = reverse("dashboard_analytics:create_walking_activity")
        future = self.client.post(
            url,
            data=json.dumps({"duration_minutes": 30, "speed_level": "normal", "activity_date": (today + timedelta(days=1)).isoformat()}),
            content_type="application/json",
        )
        invalid_speed = self.client.post(
            url,
            data=json.dumps({"duration_minutes": 30, "speed_level": "999", "activity_date": today.isoformat()}),
            content_type="application/json",
        )
        self.assertEqual(future.status_code, 400)
        self.assertEqual(invalid_speed.status_code, 400)
        self.assertEqual(WalkingActivity.objects.count(), 0)

    def test_private_dashboard_and_analytics_redirect_guests_to_login(self):
        Meal.objects.create(
            user=self.other_user, date=timezone.localdate(),
            meal_type=Meal.MealType.SARAPAN, name="Privat", estimated_cost=5000
        )
        guest = Client()
        login_url = reverse("user_profile:login")

        for protected_url in (
            reverse("dashboard_analytics:dashboard"),
            f'{reverse("dashboard_analytics:impact_analytics")}?period=7d',
            reverse("dashboard_analytics:dashboard_data_api"),
            reverse("dashboard_analytics:download_report"),
        ):
            response = guest.get(protected_url)
            self.assertEqual(response.status_code, 302)
            destination = urlparse(response.url)
            self.assertEqual(destination.path, login_url)
            self.assertEqual(parse_qs(destination.query)["next"], [protected_url])

    def test_dashboard_omits_the_removed_recommendation_section(self):
        response = self.client.get(reverse("dashboard_analytics:dashboard"))

        self.assertNotContains(response, "Pilihan hangat untuk anak kos")
        self.assertNotContains(response, "Tumis tempe kemangi 15 menit")
        self.assertNotContains(response, "Baca label gizi tanpa bingung")
        self.assertContains(response, "Komunitas KoSehat")

    def test_impact_combines_entries_and_zero_packaging_meals_as_contributions(self):
        today = timezone.localdate()
        Meal.objects.create(
            user=self.user, date=today, meal_type=Meal.MealType.SIANG,
            name="Menu tanpa kemasan", packaging_used=0
        )
        Meal.objects.create(
            user=self.user, date=today, meal_type=Meal.MealType.MALAM,
            name="Menu berkemedasan", packaging_used=2
        )
        Meal.objects.create(
            user=self.other_user, date=today, meal_type=Meal.MealType.SIANG,
            name="Menu privat", packaging_used=0
        )
        Meal.objects.create(
            user=self.user, date=today + timedelta(days=1), meal_type=Meal.MealType.SARAPAN,
            name="Menu masa depan", packaging_used=0
        )
        ImpactEntry.objects.create(user=self.user, activity_type="refill", packages_avoided=2)
        ImpactEntry.objects.create(user=self.other_user, activity_type="refill", packages_avoided=50)

        response = self.client.get(reverse("dashboard_analytics:impact_analytics"), {"period": "7d"})
        analytics = response.context["analytics"]

        self.assertEqual(analytics["summary"]["contributions"], 3)
        self.assertEqual(analytics["summary"]["impact_entries"], 2)
        self.assertEqual(analytics["meal_contribution"]["count"], 1)
        self.assertEqual(analytics["source_reduction"][0]["label"], "Sarapan")
        self.assertEqual(analytics["source_reduction"][1]["label"], "Makan Siang")
        self.assertEqual(analytics["source_reduction"][1]["value"], 1)
        self.assertEqual(sum(source["value"] for source in analytics["source_reduction"]), 1)
        self.assertEqual(analytics["all_time_contributions"], 3)
        self.assertContains(response, "Makan Siang")

    def test_source_reduction_groups_only_zero_packaging_meals_by_meal_type(self):
        today = timezone.localdate()
        zero_packaging_meals = (
            (Meal.MealType.SARAPAN, "Sarapan 1"),
            (Meal.MealType.SIANG, "Siang 1"),
            (Meal.MealType.SIANG, "Siang 2"),
            (Meal.MealType.MALAM, "Malam 1"),
            (Meal.MealType.CAMILAN, "Camilan 1"),
        )
        for meal_type, name in zero_packaging_meals:
            Meal.objects.create(
                user=self.user,
                date=today,
                meal_type=meal_type,
                name=name,
                packaging_used=0,
            )
        Meal.objects.create(
            user=self.user,
            date=today,
            meal_type=Meal.MealType.SIANG,
            name="Siang berkemedasan",
            packaging_used=1,
        )
        Meal.objects.create(
            user=self.other_user,
            date=today,
            meal_type=Meal.MealType.SIANG,
            name="Siang privat",
            packaging_used=0,
        )
        ImpactEntry.objects.create(
            user=self.user,
            activity_type="refill",
            packages_avoided=7,
        )

        analytics = self.client.get(
            reverse("dashboard_analytics:impact_analytics"), {"period": "7d"}
        ).context["analytics"]
        sources = {source["label"]: source for source in analytics["source_reduction"]}

        self.assertEqual(set(sources), {"Sarapan", "Makan Siang", "Makan Malam", "Camilan"})
        self.assertEqual(sources["Sarapan"]["value"], 1)
        self.assertEqual(sources["Makan Siang"]["value"], 2)
        self.assertEqual(sources["Makan Malam"]["value"], 1)
        self.assertEqual(sources["Camilan"]["value"], 1)
        self.assertEqual(sources["Makan Siang"]["percent"], 40)
        self.assertEqual(sources["Sarapan"]["percent"], 20)
        self.assertEqual(analytics["summary"]["contributions"], 12)

    def test_impact_meal_habit_cards_are_period_scoped_and_private(self):
        today = timezone.localdate()
        Meal.objects.create(
            user=self.user,
            date=today,
            meal_type=Meal.MealType.SIANG,
            name="Makan siang homemade tanpa kemasan",
            is_homemade=True,
            packaging_used=0,
        )
        Meal.objects.create(
            user=self.user,
            date=today,
            meal_type=Meal.MealType.SIANG,
            name="Makan siang tanpa kemasan",
            packaging_used=0,
        )
        Meal.objects.create(
            user=self.user,
            date=today - timedelta(days=1),
            meal_type=Meal.MealType.SARAPAN,
            name="Sarapan homemade tanpa kemasan",
            is_homemade=True,
            packaging_used=0,
        )
        Meal.objects.create(
            user=self.user,
            date=today - timedelta(days=40),
            meal_type=Meal.MealType.MALAM,
            name="Menu periode lalu",
            is_homemade=True,
            packaging_used=0,
        )
        Meal.objects.create(
            user=self.other_user,
            date=today,
            meal_type=Meal.MealType.CAMILAN,
            name="Menu privat pengguna lain",
            is_homemade=True,
            packaging_used=0,
        )

        response = self.client.get(
            reverse("dashboard_analytics:impact_analytics"), {"period": "7d"}
        )
        analytics = response.context["analytics"]

        self.assertEqual(analytics["summary"]["homemade_menus"], 2)
        self.assertEqual(analytics["eco_eating"]["packaging_free_menus"], 3)
        self.assertEqual(analytics["eco_eating"]["friendly_days"], 2)
        self.assertEqual(analytics["eco_eating"]["most_consistent_meal_type"], "Makan Siang")
        self.assertContains(response, "Konsistensi Memasak Sendiri")
        self.assertContains(response, "Kebiasaan Makan Ramah Lingkungan")
        self.assertNotContains(response, "Kategori paling konsisten")

    def test_impact_analytics_does_not_expose_other_users_meal_data_to_guests(self):
        Meal.objects.create(
            user=self.other_user,
            date=timezone.localdate(),
            meal_type=Meal.MealType.SIANG,
            name="Menu privat",
            is_homemade=True,
            packaging_used=0,
        )

        response = Client().get(
            reverse("dashboard_analytics:impact_analytics"), {"period": "7d"}
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.url).path, reverse("user_profile:login"))

    def test_recipe_catalog_item_and_blank_packaging_are_not_meal_contributions(self):
        Recipe.objects.create(
            title="Resep katalog saja",
            description="Belum dipilih ke Meal Planner.",
        )
        packaging_field = Meal._meta.get_field("packaging_used")

        response = self.client.get(reverse("dashboard_analytics:impact_analytics"), {"period": "7d"})
        analytics = response.context["analytics"]

        # Field ini required/non-null; Meal Planner tidak mempunyai nilai kosong
        # yang dapat ditafsirkan sebagai pilihan tanpa kemasan.
        self.assertFalse(packaging_field.null)
        self.assertEqual(analytics["meal_contribution"]["count"], 0)
        self.assertEqual(analytics["summary"]["contributions"], 0)

    def test_private_mutation_endpoints_require_login(self):
        guest = Client()

        for protected_url in (
            reverse("dashboard_analytics:save_weekly_budget"),
            reverse("dashboard_analytics:add_impact_entry"),
            reverse("dashboard_analytics:add_community_comment"),
        ):
            response = guest.post(protected_url, data="{}", content_type="application/json")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(urlparse(response.url).path, reverse("user_profile:login"))

    def test_login_returns_to_safe_next_or_dashboard_by_default(self):
        guest = Client()
        dashboard_url = reverse("dashboard_analytics:dashboard")
        login_url = reverse("user_profile:login")

        login_page = guest.get(f"{login_url}?next={dashboard_url}")
        self.assertContains(login_page, 'name="next" value="/dashboard/"')
        response = guest.post(
            login_url,
            {"username": self.user.username, "password": "test-password", "next": dashboard_url},
        )
        self.assertRedirects(response, dashboard_url, fetch_redirect_response=False)

        guest.logout()
        response = guest.post(
            login_url,
            {"username": self.user.username, "password": "test-password", "next": "https://attacker.example/dashboard/"},
        )
        self.assertRedirects(response, dashboard_url, fetch_redirect_response=False)

        guest.logout()
        response = guest.post(
            login_url,
            {"username": self.user.username, "password": "test-password"},
        )
        self.assertRedirects(response, dashboard_url, fetch_redirect_response=False)

    def test_impact_trend_uses_current_user_entries_in_three_month_period(self):
        today = timezone.localdate()
        current_period_entry = ImpactEntry.objects.create(
            user=self.user, activity_type="container", packages_avoided=3
        )
        # `recorded_on` is auto_now_add; set it explicitly to exercise the
        # earliest month of the displayed three-month range.
        current_period_entry.recorded_on = today.replace(day=1) - timedelta(days=35)
        current_period_entry.save(update_fields=["recorded_on"])
        outside_period_entry = ImpactEntry.objects.create(
            user=self.user, activity_type="bulk", packages_avoided=8
        )
        outside_period_entry.recorded_on = today - timedelta(days=100)
        outside_period_entry.save(update_fields=["recorded_on"])
        other_user_entry = ImpactEntry.objects.create(
            user=self.other_user, activity_type="fresh", packages_avoided=9
        )
        other_user_entry.recorded_on = today
        other_user_entry.save(update_fields=["recorded_on"])
        Meal.objects.create(
            user=self.user,
            date=today,
            meal_type=Meal.MealType.SIANG,
            name="Menu tanpa kemasan periode ini",
            packaging_used=0,
        )
        Meal.objects.create(
            user=self.other_user,
            date=today,
            meal_type=Meal.MealType.MALAM,
            name="Menu privat",
            packaging_used=0,
        )

        response = self.client.get(reverse("dashboard_analytics:impact_analytics"), {"period": "3m"})
        analytics = response.context["analytics"]

        self.assertEqual(analytics["summary"]["contributions"], 4)
        self.assertEqual(analytics["trend"][-1], 4)
        self.assertGreaterEqual(len(analytics["chart_points"]), 12)
        self.assertNotIn("target", analytics)
        self.assertNotContains(response, "Target")

    def test_impact_page_replaces_ranking_with_motivational_caption(self):
        response = self.client.get(reverse("dashboard_analytics:impact_analytics"))

        self.assertContains(response, "Setiap langkah kecil tetap berarti.")
        self.assertNotContains(response, "Peringkat Asrama")
        self.assertNotContains(response, "Peringkat belum tersedia")

    def test_budget_updates_once_and_uses_current_users_meal_cost(self):
        today = timezone.localdate()
        Meal.objects.create(
            user=self.user, date=today, meal_type=Meal.MealType.MALAM,
            name="Makan malam", estimated_cost=30000
        )
        url = reverse("dashboard_analytics:save_weekly_budget")
        created = self.client.post(url, data=json.dumps({"amount": 100000}), content_type="application/json")
        updated = self.client.post(url, data=json.dumps({"amount": 120000}), content_type="application/json")
        week_start = today - timedelta(days=today.weekday())

        self.assertEqual(created.status_code, 201)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(WeeklyBudget.objects.get(user=self.user, week_start=week_start).amount, 120000)
        self.assertEqual(WeeklyBudget.objects.filter(user=self.user).count(), 1)
        analytics = self.client.get(reverse("dashboard_analytics:impact_analytics")).context["analytics"]
        self.assertEqual(analytics["weekly_budget"]["spent"], 30000)

    def test_csv_is_scoped_to_current_user(self):
        ImpactEntry.objects.create(user=self.user, activity_type="refill", packages_avoided=4)
        ImpactEntry.objects.create(user=self.other_user, activity_type="refill", packages_avoided=99)
        Meal.objects.create(
            user=self.user,
            date=timezone.localdate(),
            meal_type=Meal.MealType.SIANG,
            name="Menu CSV",
            packaging_used=0,
        )
        Meal.objects.create(
            user=self.other_user,
            date=timezone.localdate(),
            meal_type=Meal.MealType.SIANG,
            name="Menu CSV privat",
            packaging_used=0,
        )

        response = self.client.get(reverse("dashboard_analytics:download_report"), {"period": "7d"})
        content = response.content.decode("utf-8-sig").replace("\r\n", "\n")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Kontribusi pengurangan kemasan,5", content)
        self.assertIn("Menu dengan 0 kemasan sekali pakai tercatat (Meal Planner),1", content)
        self.assertIn("Konsistensi memasak sendiri (menu),0", content)
        self.assertNotIn(",99", content)

    def test_community_requires_login_and_binds_author(self):
        guest = Client()
        url = reverse("dashboard_analytics:add_community_comment")
        response = guest.post(url, data=json.dumps({"content": "Halo"}), content_type="application/json")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            urlparse(response.url).path,
            reverse("user_profile:login"),
        )
        response = self.client.post(
            url, data=json.dumps({"content": "<script>alert(1)</script>"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(CommunityComment.objects.get().user, self.user)

    def test_community_comment_owner_can_delete_their_main_comment_and_replies(self):
        comment = CommunityComment.objects.create(user=self.user, content="Komentar saya")
        reply = CommunityComment.objects.create(
            user=self.user,
            parent=comment,
            content="Balasan saya",
        )

        reply_response = self.client.post(
            reverse("dashboard_analytics:delete_community_comment", args=[reply.pk])
        )
        comment_response = self.client.post(
            reverse("dashboard_analytics:delete_community_comment", args=[comment.pk])
        )

        self.assertEqual(reply_response.status_code, 200)
        self.assertEqual(reply_response.json()["parent_id"], comment.pk)
        self.assertFalse(CommunityComment.objects.filter(pk=reply.pk).exists())
        self.assertEqual(comment_response.status_code, 200)
        self.assertFalse(CommunityComment.objects.filter(pk=comment.pk).exists())

    def test_community_delete_rejects_other_user_and_deletes_replies_with_parent(self):
        comment = CommunityComment.objects.create(user=self.other_user, content="Komentar teman")
        reply = CommunityComment.objects.create(
            user=self.other_user,
            parent=comment,
            content="Balasan teman",
        )

        other_comment = self.client.post(
            reverse("dashboard_analytics:delete_community_comment", args=[comment.pk])
        )
        other_reply = self.client.post(
            reverse("dashboard_analytics:delete_community_comment", args=[reply.pk])
        )

        self.assertEqual(other_comment.status_code, 404)
        self.assertEqual(other_reply.status_code, 404)
        self.assertTrue(CommunityComment.objects.filter(pk=comment.pk).exists())
        self.assertTrue(CommunityComment.objects.filter(pk=reply.pk).exists())

        self.client.force_login(self.other_user)
        own_comment = self.client.post(
            reverse("dashboard_analytics:delete_community_comment", args=[comment.pk])
        )
        self.assertEqual(own_comment.status_code, 200)
        self.assertFalse(CommunityComment.objects.filter(pk=comment.pk).exists())
        self.assertFalse(CommunityComment.objects.filter(pk=reply.pk).exists())

    def test_community_delete_requires_csrf_token(self):
        comment = CommunityComment.objects.create(user=self.user, content="Komentar saya")
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        delete_url = reverse("dashboard_analytics:delete_community_comment", args=[comment.pk])

        self.assertEqual(csrf_client.post(delete_url).status_code, 403)
        csrf_client.get(reverse("dashboard_analytics:dashboard"))
        csrf_token = csrf_client.cookies["csrftoken"].value
        response = csrf_client.post(delete_url, HTTP_X_CSRFTOKEN=csrf_token)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(CommunityComment.objects.filter(pk=comment.pk).exists())

    def test_community_api_exposes_delete_control_only_to_the_owner(self):
        comment = CommunityComment.objects.create(user=self.user, content="Komentar saya")
        own_reply = CommunityComment.objects.create(
            user=self.user,
            parent=comment,
            content="Balasan saya",
        )
        CommunityComment.objects.create(
            user=self.other_user,
            parent=comment,
            content="Balasan teman",
        )

        own_response = self.client.get(
            reverse("dashboard_analytics:community_comments_api")
        )
        own_comment = own_response.json()["comments"][0]
        self.assertTrue(own_comment["can_delete"])
        self.assertTrue(
            next(reply for reply in own_comment["replies"] if reply["id"] == own_reply.pk)["can_delete"]
        )
        self.assertFalse(
            next(reply for reply in own_comment["replies"] if reply["id"] != own_reply.pk)["can_delete"]
        )

        self.client.force_login(self.other_user)
        other_response = self.client.get(
            reverse("dashboard_analytics:community_comments_api")
        )
        other_comment = other_response.json()["comments"][0]
        self.assertFalse(other_comment["can_delete"])
