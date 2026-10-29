# Generated for Module 4's temporary habit-log storage.
import django.conf
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(django.conf.settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="HabitEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("habit_type", models.CharField(choices=[("water", "Hidrasi"), ("steps", "Langkah"), ("sleep", "Durasi tidur"), ("active", "Gerak aktif")], max_length=12)),
                ("amount", models.PositiveIntegerField()),
                ("recorded_on", models.DateField(auto_now_add=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="kosehat_habit_entries", to=django.conf.settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
