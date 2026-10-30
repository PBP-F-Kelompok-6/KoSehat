from django.db import models
from django.contrib.auth.models import User

class Habit(models.Model):
    CATEGORY_CHOICES = [
        ('water', 'Hidrasi'),
        ('food', 'Pola Makan'),
        ('exercise', 'Olahraga'),
        ('sleep', 'Kualitas Tidur'),
        ('mindfulness', 'Eco-Mindfulness'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='habits')
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='mindfulness')
    target_value = models.IntegerField(default=1, help_text="Target harian")
    unit = models.CharField(max_length=50, default="kali", help_text="ml, langkah, menit, kali")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.user.username}"

class HabitLog(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='logs')
    date = models.DateField()
    current_value = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    logged_time = models.TimeField(auto_now=True)

    class Meta:
        unique_together = ('habit', 'date')

class SleepLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sleep_logs')
    date = models.DateField()
    duration_minutes = models.IntegerField(default=0, help_text="Durasi tidur dalam menit (default 7j 24m)")
    target_hours = models.FloatField(default=7.5, help_text="Target tidur harian dalam jam")

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f"Sleep {self.date} - {self.user.username} ({self.duration_minutes}m)"

class EnergyLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='energy_logs')
    date = models.DateField()
    energy_level = models.IntegerField(default=8, help_text="Skala 1 - 10")
    focus_minutes = models.IntegerField(default=180, help_text="Target waktu fokus dalam menit")
    logged_focus_minutes = models.IntegerField(default=0, help_text="Waktu fokus yang telah dilalui dalam menit")

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f"Energy {self.energy_level}/10 - {self.user.username} ({self.date})"

class UserStreak(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='streak')
    current_streak = models.IntegerField(default=0)
    best_streak = models.IntegerField(default=0)
    last_checked_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - Streak: {self.current_streak} (Best: {self.best_streak})"