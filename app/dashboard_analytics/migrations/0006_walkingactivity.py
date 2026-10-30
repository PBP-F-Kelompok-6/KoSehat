from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("dashboard_analytics", "0005_weeklybudget_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="WalkingActivity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("duration_minutes", models.PositiveIntegerField()),
                ("speed_level", models.CharField(choices=[("slow", "Lambat"), ("normal", "Normal"), ("fast", "Cepat")], default="normal", max_length=10)),
                ("activity_date", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="kosehat_walking_activities", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-activity_date", "-created_at"]},
        ),
        migrations.AddIndex(
            model_name="walkingactivity",
            index=models.Index(fields=["user", "activity_date"], name="dashboard_a_user_id_16763c_idx"),
        ),
    ]
