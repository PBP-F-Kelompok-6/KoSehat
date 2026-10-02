from django.conf import settings
from django.db import models
from django.utils import timezone


class Meal(models.Model):
    """Satu entri menu makan dalam jadwal harian."""

    class MealType(models.TextChoices):
        SARAPAN = 'sarapan', 'Sarapan'
        SIANG = 'siang', 'Makan Siang'
        MALAM = 'malam', 'Makan Malam'
        CAMILAN = 'camilan', 'Camilan'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='meals',
    )
    date = models.DateField(default=timezone.localdate)
    meal_type = models.CharField(max_length=10, choices=MealType.choices)
    name = models.CharField(max_length=120)
    estimated_cost = models.PositiveIntegerField(
        default=0, help_text='Perkiraan biaya dalam Rupiah'
    )
    calories = models.PositiveIntegerField(
        null=True, blank=True, help_text='Opsional, dalam kkal'
    )
    # Eco-diet
    is_homemade = models.BooleanField(
        default=False, help_text='Masak sendiri, bukan makanan cepat saji'
    )
    packaging_avoided = models.PositiveSmallIntegerField(
        default=0, help_text='Jumlah kemasan sekali pakai yang dihindari'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'created_at']

    def __str__(self):
        return f'{self.date} - {self.get_meal_type_display()}: {self.name}'
