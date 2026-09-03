from django.contrib.auth import get_user_model
from django.utils import timezone

from gym_journal.models import Exercise, Muscle, Workout, WorkoutSet

User = get_user_model()


def make_user(username="athlete", password="test-password"):
    return User.objects.create_user(username=username, password=password)


def make_muscle(name="Chest"):
    return Muscle.objects.create(name=name)


def make_exercise(
    name="Bench Press",
    category=Exercise.Category.FREE_WEIGHT,
    muscles=None,
):
    exercise = Exercise.objects.create(name=name, category=category)
    if muscles:
        exercise.targeted_muscles.set(muscles)
    return exercise


def make_workout(user=None, started_at=None, ended_at=None):
    if user is None:
        user = User.objects.order_by("pk").first() or make_user()
    return Workout.objects.create(
        user=user,
        started_at=started_at or timezone.now(),
        ended_at=ended_at,
    )


def make_workout_set(workout, exercise, **overrides):
    defaults = {
        "logged_at": timezone.now(),
        "reps": 8,
        "weight": 135,
    }
    defaults.update(overrides)
    return WorkoutSet.objects.create(workout=workout, exercise=exercise, **defaults)
