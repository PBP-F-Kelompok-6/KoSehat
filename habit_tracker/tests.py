from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from habit_tracker.models import Habit, HabitLog, UserStreak, EnergyLog


class HabitTrackerTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='ranu', password='password123')
        self.client.login(username='ranu', password='password123')
        self.habit = Habit.objects.create(
            user=self.user, 
            title="Minum Air", 
            category="water",
            target_value=2000, 
            unit="ml"
        )

    def test_habit_tracker_page_status(self):
        response = self.client.get(reverse('habit_tracker:index'))
        self.assertEqual(response.status_code, 200)

    def test_get_habits_json(self):
        response = self.client.get(reverse('habit_tracker:get_habits'))
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIn('habits', json_data)
        self.assertIn('summary', json_data)
        self.assertEqual(json_data['summary']['energy_level'], 8)

    def test_add_habit_ajax(self):
        response = self.client.post(reverse('habit_tracker:add_habit'), {
            'title': 'Olahraga Pagi',
            'category': 'exercise',
            'target_value': 15,
            'unit': 'menit'
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Habit.objects.filter(user=self.user).count(), 2)

    def test_toggle_habit_ajax(self):
        response = self.client.post(reverse('habit_tracker:toggle_habit', args=[self.habit.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['is_completed'])

    def test_delete_habit_ajax(self):
        response = self.client.post(reverse('habit_tracker:delete_habit', args=[self.habit.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Habit.objects.filter(user=self.user).count(), 0)

    def test_log_energy_ajax(self):
        response = self.client.post(reverse('habit_tracker:log_energy'), {
            'energy_level': 9,
            'focus_minutes': 210,
        })
        self.assertEqual(response.status_code, 200)
        
        today = timezone.now().date()
        energy_log = EnergyLog.objects.get(user=self.user, date=today)
        self.assertEqual(energy_log.energy_level, 9)
        self.assertEqual(energy_log.focus_minutes, 210)


class StreakTrackerTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='ranu', password='password123')
        self.client.login(username='ranu', password='password123')
        
        self.habit = Habit.objects.create(
            user=self.user, 
            title="Olahraga Pagi", 
            category="exercise"
        )
        # Set created_at ke 2 hari lalu agar habit terdaftar saat evaluasi hari kemarin
        two_days_ago = timezone.now() - timedelta(days=2)
        Habit.objects.filter(id=self.habit.id).update(created_at=two_days_ago)

    def test_new_user_streak_is_zero(self):
        response = self.client.get(reverse('habit_tracker:get_habits'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['summary']['streak'], 0)
        self.assertEqual(data['summary']['best_streak'], 0)

    def test_streak_increments_on_next_day_after_all_completed(self):
        yesterday = timezone.now().date() - timedelta(days=1)
        
        # Simulasikan kebiasaan kemarin selesai
        HabitLog.objects.create(habit=self.habit, date=yesterday, current_value=1, is_completed=True)
        
        # Inisialisasi last_checked_date ke kemarin
        UserStreak.objects.create(user=self.user, current_streak=0, best_streak=0, last_checked_date=yesterday)

        # Hari ini dibuka -> streak bertambah 1
        response = self.client.get(reverse('habit_tracker:get_habits'))
        data = response.json()
        self.assertEqual(data['summary']['streak'], 1)
        self.assertEqual(data['summary']['best_streak'], 1)

    def test_streak_resets_if_habits_not_completed(self):
        yesterday = timezone.now().date() - timedelta(days=1)
        
        # Simulasikan kebiasaan kemarin BELUM selesai
        HabitLog.objects.create(habit=self.habit, date=yesterday, current_value=0, is_completed=False)
        
        # Inisialisasi streak awal bernilai 3
        UserStreak.objects.create(user=self.user, current_streak=3, best_streak=5, last_checked_date=yesterday)

        # Hari ini dibuka -> streak direset ke 0
        response = self.client.get(reverse('habit_tracker:get_habits'))
        data = response.json()
        self.assertEqual(data['summary']['streak'], 0)
        self.assertEqual(data['summary']['best_streak'], 5)