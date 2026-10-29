import json

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import HabitEntry, ImpactEntry


class DashboardAnalyticsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="prajna",
            password="test-password",
            first_name="Prajna",
        )
        self.other_user = get_user_model().objects.create_user(
            username="teman",
            password="test-password",
        )
        self.client.force_login(self.user)

    def _habit(self, user, habit_type, amount, recorded_on):
        entry = HabitEntry.objects.create(
            user=user,
            habit_type=habit_type,
            amount=amount,
        )
        HabitEntry.objects.filter(pk=entry.pk).update(recorded_on=recorded_on)
        return entry

    def _impact(self, user, activity_type, packages_avoided, recorded_on):
        entry = ImpactEntry.objects.create(
            user=user,
            activity_type=activity_type,
            packages_avoided=packages_avoided,
        )
        ImpactEntry.objects.filter(pk=entry.pk).update(recorded_on=recorded_on)
        return entry

    def test_dashboard_aggregates_only_current_users_entries_today(self):
        today = timezone.localdate()
        self._habit(self.user, "water", 750, today)
        self._habit(self.user, "water", 250, today)
        self._habit(self.user, "steps", 3000, today)
        self._habit(self.user, "sleep", 420, today - timedelta(days=1))
        self._habit(self.other_user, "water", 2000, today)

        response = self.client.get(reverse("dashboard_analytics:dashboard"))
        dashboard = response.context["dashboard"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(dashboard["hydration_ml"], 1000)
        self.assertEqual(dashboard["steps"]["value"], "3.000")
        self.assertEqual(dashboard["sleep"]["value"], "0j 00m")
        self.assertEqual(dashboard["score"], 44)

    def test_dashboard_api_returns_empty_database_state(self):
        response = self.client.get(reverse("dashboard_analytics:dashboard_data_api"))
        dashboard = response.json()["dashboard"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(dashboard["hydration_ml"], 0)
        self.assertIsNone(dashboard["score"])
        self.assertEqual(dashboard["month_impact"], 0)

    def test_impact_period_and_source_breakdown_use_actual_entries(self):
        today = timezone.localdate()
        self._impact(self.user, "refill", 2, today)
        self._impact(self.user, "container", 3, today - timedelta(days=1))
        self._impact(self.user, "bulk", 9, today - timedelta(days=7))
        self._impact(self.other_user, "refill", 20, today)

        response = self.client.get(
            reverse("dashboard_analytics:impact_analytics"),
            {"period": "7d"},
        )
        analytics = response.context["analytics"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(analytics["summary"]["packages"], 5)
        self.assertEqual(analytics["trend"][-1], 5)
        self.assertEqual(analytics["source_reduction"][0]["value"], 2)
        self.assertEqual(analytics["source_reduction"][1]["value"], 3)
        self.assertEqual(analytics["source_reduction"][2]["value"], 0)

    def test_impact_page_handles_empty_period(self):
        response = self.client.get(
            reverse("dashboard_analytics:impact_analytics"),
            {"period": "year"},
        )
        analytics = response.context["analytics"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(analytics["summary"]["packages"], 0)
        self.assertTrue(all(point["value"] == 0 for point in analytics["chart_points"]))

    def test_impact_entry_endpoint_validates_and_persists(self):
        url = reverse("dashboard_analytics:add_impact_entry")
        invalid_response = self.client.post(
            url,
            data=json.dumps({"activity_type": "unknown", "packages_avoided": 2}),
            content_type="application/json",
        )
        valid_response = self.client.post(
            url,
            data=json.dumps({"activity_type": "refill", "packages_avoided": 2}),
            content_type="application/json",
        )

        self.assertEqual(invalid_response.status_code, 400)
        self.assertEqual(valid_response.status_code, 201)
        self.assertEqual(
            ImpactEntry.objects.filter(user=self.user, packages_avoided=2).count(),
            1,
        )

    def test_entry_endpoints_reject_non_object_json_payloads(self):
        response = self.client.post(
            reverse("dashboard_analytics:add_habit_entry"),
            data="[]",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(HabitEntry.objects.count(), 0)

    def test_guest_entries_are_isolated_by_session(self):
        guest_client = Client()
        other_guest_client = Client()
        url = reverse("dashboard_analytics:add_habit_entry")

        response = guest_client.post(
            url,
            data=json.dumps({"habit_type": "water", "amount": 500}),
            content_type="application/json",
        )
        own_dashboard = guest_client.get(
            reverse("dashboard_analytics:dashboard_data_api")
        ).json()["dashboard"]
        other_dashboard = other_guest_client.get(
            reverse("dashboard_analytics:dashboard_data_api")
        ).json()["dashboard"]

        self.assertEqual(response.status_code, 201)
        self.assertEqual(own_dashboard["hydration_ml"], 500)
        self.assertEqual(other_dashboard["hydration_ml"], 0)

    def test_csv_report_uses_filtered_database_aggregates(self):
        today = timezone.localdate()
        self._impact(self.user, "refill", 4, today)
        self._impact(self.other_user, "refill", 99, today)

        response = self.client.get(
            reverse("dashboard_analytics:download_report"),
            {"period": "7d"},
        )
        content = response.content.decode("utf-8-sig")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Kemasan dihindari (item),4", content)
        self.assertIn("Isi ulang air minum,4", content)
        self.assertNotIn(",99", content)
