from django.conf import settings
from django.db import models


class HabitEntry(models.Model):
    """Catatan kebiasaan harian yang dipakai Dashboard sampai modul Habit Tracker terintegrasi."""

    HABIT_TYPES = [
        ("water", "Hidrasi"),
        ("steps", "Langkah"),
        ("sleep", "Durasi tidur"),
        ("active", "Gerak aktif"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="kosehat_habit_entries",
    )
    anonymous_session_key = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        db_index=True,
        help_text="Pemilik catatan saat pengguna belum masuk.",
    )
    habit_type = models.CharField(max_length=12, choices=HABIT_TYPES)
    amount = models.PositiveIntegerField()
    recorded_on = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_habit_type_display()}: {self.amount} ({self.recorded_on})"


class ImpactEntry(models.Model):
    """Catatan aktivitas yang mengurangi sampah kemasan."""

    ACTIVITY_TYPES = [
        ("refill", "Isi ulang air minum"),
        ("container", "Bawa wadah makan"),
        ("bulk", "Belanja curah / pasar"),
        ("fresh", "Masak dari bahan segar"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="kosehat_impact_entries",
    )
    anonymous_session_key = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        db_index=True,
        help_text="Pemilik catatan saat pengguna belum masuk.",
    )
    activity_type = models.CharField(
        max_length=12,
        choices=ACTIVITY_TYPES,
    )
    packages_avoided = models.PositiveIntegerField(default=1)
    recorded_on = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.get_activity_type_display()}: "
            f"{self.packages_avoided} kemasan "
            f"({self.recorded_on})"
        )


class CommunityComment(models.Model):
    """Postingan dan balasan pada komunitas KoSehat."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kosehat_community_comments",
    )
    content = models.TextField(max_length=1000)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.content[:50]
