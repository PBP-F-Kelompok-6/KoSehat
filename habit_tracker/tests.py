from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from habit_tracker.models import Habit, HabitLog

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
        self.assertTemplateUsed(response, 'habit_tracker.html')

    def test_get_habits_json(self):
        response = self.client.get(reverse('habit_tracker:get_habits'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('habits', response.json())

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