from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    GOAL_CHOICES = [
        ('WEIGHT_LOSS', 'Menurunkan Berat Badan'),
        ('MAINTAIN_WEIGHT', 'Menjaga Berat Badan'),
        ('MUSCLE_GAIN', 'Meningkatkan Massa Otot'),
        ('EAT_HEALTHIER', 'Pola Makan Lebih Sehat & Sustainable'),
        ('INCREASE_ENERGY', 'Meningkatkan Tingkat Energi'),
    ]

    ACTIVITY_CHOICES = [
        ('SEDENTARY', 'Sedentari (Jarang Berolahraga)'),
        ('LIGHT', 'Ringan (Olahraga 1-3 hari/minggu)'),
        ('MODERATE', 'Sedang (Olahraga 3-5 hari/minggu)'),
        ('ACTIVE', 'Aktif (Olahraga 6-7 hari/minggu)'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Target & Preferensi Kesehatan
    health_goal = models.CharField(max_length=50, choices=GOAL_CHOICES, default='EAT_HEALTHIER')
    activity_level = models.CharField(max_length=50, choices=ACTIVITY_CHOICES, default='MODERATE')
    daily_calorie_target = models.PositiveIntegerField(default=2000, help_text="Target kalori harian (kcal)")
    daily_water_intake_target = models.FloatField(default=2.0, help_text="Target konsumsi air harian (liter)")
    dietary_restrictions = models.CharField(max_length=255, blank=True, null=True, help_text="Contoh: Vegetarian, Lactose-free, Tanpa Kacang")
    
    # Informasi Profil
    bio = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=100, default='Asrama UI, Depok')

    def __str__(self):
        return f"Profil {self.user.username}"


# Signal otomatis membuat UserProfile saat User baru terdaftar/login
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        instance.profile.save()