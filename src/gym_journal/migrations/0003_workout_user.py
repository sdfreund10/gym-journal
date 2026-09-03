import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def assign_workouts_to_earliest_user(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL)
    Workout = apps.get_model("gym_journal", "Workout")

    earliest_user = User.objects.order_by("pk").first()
    if earliest_user is None:
        Workout.objects.all().delete()
        return

    Workout.objects.filter(user__isnull=True).update(user=earliest_user)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("gym_journal", "0002_workoutset_optional_duration"),
    ]

    operations = [
        migrations.AddField(
            model_name="workout",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="workouts",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(assign_workouts_to_earliest_user, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="workout",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="workouts",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
