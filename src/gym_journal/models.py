from typing import Optional
from datetime import datetime
from django.conf import settings
from django.db import models, transaction
from django.db.models import Max
from django.core.exceptions import ValidationError
from django.utils import timezone


class Muscle(models.Model):
    name = models.TextField(unique=True)

    def __str__(self):
        return self.name


class Exercise(models.Model):
    class Category(models.TextChoices):
        BODYWEIGHT = "bodyweight", "Bodyweight"
        DUMBBELL = "dumbbell", "Dumbbell"
        FREE_WEIGHT = "free_weight", "Free weight"
        MACHINE = "machine", "Machine"
        TIMED = "timed", "Timed"

    name = models.TextField(unique=True)
    category = models.CharField(choices=Category.choices)
    targeted_muscles = models.ManyToManyField(Muscle)

    def __str__(self):
        return self.name

    # return all exercises with the 5 most recently used first
    @classmethod
    def ordered_by_recency(cls, user):
        recent_ids = WorkoutSet.recent_ids(user)
        recent_index = {id: index for index, id in enumerate(recent_ids)}

        return sorted(
            cls.objects.all().order_by("name"),
            key=lambda ex: (recent_index.get(ex.pk, 999), ex.name.lower()),
        )

    def last_weight(self, user):
        last_set = (
            WorkoutSet.objects.filter(
                exercise=self,
                weight__isnull=False,
                workout__user=user,
            )
            .order_by("-logged_at")
            .first()
        )
        return last_set.weight if last_set else None


class WorkoutQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(user=user)

    def active(self):
        return self.filter(ended_at__isnull=True)


class Workout(models.Model):
    # properties
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workouts",
    )
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    exercises = models.ManyToManyField(Exercise, through="WorkoutSet")

    # query helpers
    objects = WorkoutQuerySet.as_manager()

    def __str__(self):
        return f'Workout {self.started_at:%Y-%m-%d %H:%M}'

    @classmethod
    @transaction.atomic
    def start(cls, user):
        active_workout = cls.objects.for_user(user).active().first()
        if active_workout:
            raise ValidationError("There is already an active workout.")
        new_workout = cls(user=user, started_at=timezone.now())

        new_workout.save()

        return new_workout

    def finish(self):
        self.ended_at = timezone.now()
        self.save()

    def last_set_logged_at(self) -> Optional[datetime]:
        return self.workoutset_set.aggregate(Max("logged_at"))["logged_at__max"]

    def last_activity_at(self) -> datetime:
        latest_set = self.last_set_logged_at()
        if latest_set is None:
            return self.started_at
        return max(self.started_at, latest_set)


class WorkoutSet(models.Model):
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE)
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    logged_at = models.DateTimeField()
    weight = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    reps = models.IntegerField(null=True, blank=True) # null if timed exercise
    duration_seconds = models.IntegerField(null=True, blank=True, validators=[]) # null for all but timed
    set_number = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workout", "exercise", "set_number"], name="unique_set_number_per_workout_exercise"
            )
        ]

    @classmethod
    def recent_ids(cls, user, limit=5):
        ids = (
            cls.objects.filter(workout__user=user)
            .order_by("-logged_at")
            .values_list("exercise_id", flat=True)
        )
        uniq_ids = []
        for id in ids:
            if id not in uniq_ids:
                uniq_ids.append(id)
            if len(uniq_ids) >= limit:
                break
        return uniq_ids

    @classmethod
    def next_set_number(cls, workout, exercise):
        if not workout or not exercise:
            raise ValidationError("Workout and exercise must be set.")

        max_set_number = cls.objects.filter(workout=workout, exercise=exercise).aggregate(Max("set_number"))["set_number__max"]
        return max_set_number + 1 if max_set_number else 1


    def assign_next_set_number(self):
        if self.workout_id and self.exercise_id:
            self.set_number = self.__class__.next_set_number(self.workout, self.exercise)

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self._state.adding:
            self.assign_next_set_number()
        super().save(*args, **kwargs)

    def clean(self):
        # Assign before unique-constraint validation so create + full_clean works.
        if self._state.adding:
            self.assign_next_set_number()
        super().clean()
        if self.exercise.category != Exercise.Category.TIMED:
            if self.reps is None:
                raise ValidationError("Reps must be set of non-timed exercises.")

        if self.exercise.category == Exercise.Category.TIMED:
            if self.duration_seconds is None:
                raise ValidationError("Duration must be set for timed exercises.")
