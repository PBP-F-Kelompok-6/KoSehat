from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Habit(models.Model):
    CATEGORY_CHOICES = [
        ("water", "Hidrasi"),
        ("food", "Pola Makan"),
        ("exercise", "Olahraga"),
        ("sleep", "Kualitas Tidur"),
        ("mindfulness", "Eco-Mindfulness"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="habits",
    )
    title = models.CharField(max_length=255)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="mindfulness",
    )
    target_value = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    unit = models.CharField(max_length=50, default="kali")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-is_active", "created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["user", "category"]),
        ]

    def archive(self):
        self.is_active = False
        self.archived_at = timezone.now()
        self.save(update_fields=["is_active", "archived_at"])

    def __str__(self):
        return f"{self.title} - {self.user.username}"


class HabitLog(models.Model):
    habit = models.ForeignKey(
        Habit,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    date = models.DateField()
    current_value = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    logged_time = models.TimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date", "habit__title"]
        constraints = [
            models.UniqueConstraint(
                fields=["habit", "date"],
                name="unique_habit_log_per_day",
            ),
        ]
        indexes = [
            models.Index(fields=["habit", "date"]),
            models.Index(fields=["date"]),
        ]

    def save(self, *args, **kwargs):
        if self.current_value >= self.habit.target_value:
            self.current_value = self.habit.target_value
            self.is_completed = True
        else:
            self.is_completed = False

        if self.current_value > 0 and self.logged_time is None:
            self.logged_time = timezone.localtime().time()

        super().save(*args, **kwargs)

    @property
    def progress_percent(self):
        if self.habit.target_value <= 0:
            return 0

        return min(
            100,
            round((self.current_value / self.habit.target_value) * 100),
        )

    def __str__(self):
        return f"{self.habit.title} - {self.date}"


class SleepLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sleep_logs",
    )
    date = models.DateField()
    duration_minutes = models.PositiveIntegerField(default=0)
    target_hours = models.FloatField(
        default=7.5,
        validators=[
            MinValueValidator(1.0),
            MaxValueValidator(24.0),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "date"],
                name="unique_sleep_log_per_day",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "date"]),
        ]

    @property
    def target_minutes(self):
        return round(self.target_hours * 60)

    @property
    def sleep_status(self):
        difference = self.duration_minutes - self.target_minutes

        if difference < -30:
            return "kurang"
        if difference > 60:
            return "lebih"
        return "sesuai"

    def __str__(self):
        return f"Sleep {self.date} - {self.user.username}"


class EnergyLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="energy_logs",
    )
    date = models.DateField()
    focus_minutes = models.PositiveIntegerField(default=180)
    logged_focus_minutes = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "date"],
                name="unique_energy_log_per_day",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "date"]),
        ]

    @property
    def focus_target_reached(self):
        return (
            self.focus_minutes > 0
            and self.logged_focus_minutes >= self.focus_minutes
        )

    def __str__(self):
        return f"Energy {self.date} - {self.user.username}"


class HydrationLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hydration_logs",
    )
    date = models.DateField()
    amount_ml = models.PositiveIntegerField(default=0)
    target_ml = models.PositiveIntegerField(
        default=2500,
        validators=[MinValueValidator(1)],
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "date"],
                name="unique_hydration_log_per_day",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "date"]),
        ]

    @property
    def remaining_ml(self):
        return max(self.target_ml - self.amount_ml, 0)

    @property
    def progress_percent(self):
        if self.target_ml <= 0:
            return 0

        return min(
            100,
            round(self.amount_ml / self.target_ml * 100),
        )

    @property
    def target_reached(self):
        return self.amount_ml >= self.target_ml

    def __str__(self):
        return f"Hydration {self.date} - {self.user.username}"


class UserStreak(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="streak",
    )
    current_streak = models.PositiveIntegerField(default=0)
    best_streak = models.PositiveIntegerField(default=0)
    last_checked_date = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"Streak: {self.current_streak} "
            f"(Best: {self.best_streak})"
        )
