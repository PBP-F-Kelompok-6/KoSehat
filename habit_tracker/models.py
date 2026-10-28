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
    target_value = models.IntegerField(default=1, help_text="Target harian (misal 2000 ml atau 1 kali)")
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
    duration_hours = models.FloatField(default=7.5)
    quality_score = models.IntegerField(default=8) # Scale 1-10

    class Meta:
        unique_together = ('user', 'date')