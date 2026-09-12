from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone

from gym_journal.models import Exercise, Workout, WorkoutSet

from .helpers import (
    make_exercise,
    make_muscle,
    make_user,
    make_workout,
    make_workout_set,
)


class MuscleModelTests(TestCase):
    def test_create_muscle(self):
        muscle = make_muscle("Back")
        self.assertEqual(muscle.name, "Back")
        self.assertEqual(str(muscle), "Back")

    def test_muscle_name_must_be_unique(self):
        make_muscle("Legs")
        with self.assertRaises(IntegrityError):
            make_muscle("Legs")


class ExerciseModelTests(TestCase):
    def test_create_exercise_with_category_and_muscles(self):
        chest = make_muscle("Chest")
        exercise = make_exercise(
            name="Incline Press",
            category=Exercise.Category.DUMBBELL,
            muscles=[chest],
        )

        self.assertEqual(exercise.name, "Incline Press")
        self.assertEqual(exercise.category, Exercise.Category.DUMBBELL)
        self.assertEqual(list(exercise.targeted_muscles.all()), [chest])
        self.assertEqual(str(exercise), "Incline Press")

    def test_exercise_name_must_be_unique(self):
        make_exercise(name="Squat")
        with self.assertRaises(IntegrityError):
            make_exercise(name="Squat")


class WorkoutQuerySetTests(TestCase):
    def test_active_returns_only_unfinished_workouts(self):
        user = make_user()
        active = make_workout(user=user)
        finished = make_workout(user=user, ended_at=timezone.now())

        active_ids = list(Workout.objects.active().values_list("id", flat=True))

        self.assertIn(active.id, active_ids)
        self.assertNotIn(finished.id, active_ids)

    def test_for_user_scopes_to_owner(self):
        alice = make_user("alice")
        bob = make_user("bob")
        alice_workout = make_workout(user=alice)
        make_workout(user=bob)

        self.assertEqual(
            list(Workout.objects.for_user(alice).values_list("id", flat=True)),
            [alice_workout.id],
        )


class WorkoutModelTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.exercise = make_exercise()

    def test_finish_sets_ended_at(self):
        workout = make_workout(user=self.user)
        self.assertIsNone(workout.ended_at)

        workout.finish()

        workout.refresh_from_db()
        self.assertIsNotNone(workout.ended_at)

    def test_start_creates_active_workout(self):
        workout = Workout.start(self.user)

        self.assertEqual(workout.user, self.user)
        self.assertIsNone(workout.ended_at)
        self.assertEqual(Workout.objects.for_user(self.user).active().count(), 1)

    def test_start_raises_when_workout_already_active(self):
        Workout.start(self.user)

        with self.assertRaises(ValidationError):
            Workout.start(self.user)

    def test_start_allows_active_workout_for_another_user(self):
        other = make_user("other")
        Workout.start(self.user)
        other_workout = Workout.start(other)

        self.assertEqual(other_workout.user, other)
        self.assertEqual(Workout.objects.active().count(), 2)

    def test_last_set_logged_at_returns_latest_logged_set(self):
        workout = Workout.start(self.user)
        workout_set = make_workout_set(workout=workout, exercise=self.exercise)
        self.assertEqual(workout.last_set_logged_at(), workout_set.logged_at)

    def test_last_set_logged_at_handles_no_sets(self):
        workout = Workout.start(self.user)
        self.assertEqual(workout.last_set_logged_at(), None)

    def test_last_activity_at_handles_no_sets(self):
        workout = Workout.start(self.user)
        self.assertEqual(workout.last_activity_at(), workout.started_at)

    def test_last_activity_at_returns_latest_set(self):
        workout = Workout.start(self.user)
        workout_set = make_workout_set(
            workout=workout,
            exercise=self.exercise,
            logged_at=timezone.now(),
        )
        self.assertEqual(workout.last_activity_at(), workout_set.logged_at)


class WorkoutSetRecentIdsTests(TestCase):
    def test_recent_ids_returns_unique_exercises_by_recency(self):
        user = make_user()
        workout = make_workout(user=user)
        squat = make_exercise(name="Squat")
        bench = make_exercise(name="Bench Press")
        pullup = make_exercise(name="Pull-up")

        now = timezone.now()
        make_workout_set(
            workout,
            squat,
            logged_at=now - timedelta(minutes=30),
        )
        make_workout_set(
            workout,
            bench,
            logged_at=now - timedelta(minutes=20),
        )
        make_workout_set(
            workout,
            squat,
            logged_at=now - timedelta(minutes=10),
        )
        make_workout_set(
            workout,
            pullup,
            logged_at=now - timedelta(minutes=5),
        )

        self.assertEqual(
            WorkoutSet.recent_ids(user, limit=3),
            [pullup.id, squat.id, bench.id],
        )

    def test_recent_ids_are_scoped_to_user(self):
        alice = make_user("alice")
        bob = make_user("bob")
        alice_workout = make_workout(user=alice)
        bob_workout = make_workout(user=bob)
        squat = make_exercise(name="Squat")
        bench = make_exercise(name="Bench Press")

        make_workout_set(alice_workout, squat)
        make_workout_set(bob_workout, bench)

        self.assertEqual(WorkoutSet.recent_ids(alice), [squat.id])
        self.assertEqual(WorkoutSet.recent_ids(bob), [bench.id])


class WorkoutSetValidationTests(TestCase):
    def test_non_timed_exercise_requires_reps(self):
        workout = make_workout()
        exercise = make_exercise(category=Exercise.Category.BODYWEIGHT)
        workout_set = WorkoutSet(
            workout=workout,
            exercise=exercise,
            logged_at=timezone.now(),
            reps=None,
        )

        with self.assertRaises(ValidationError):
            workout_set.full_clean()

    def test_timed_exercise_requires_duration(self):
        workout = make_workout()
        exercise = make_exercise(
            name="Plank",
            category=Exercise.Category.TIMED,
        )
        workout_set = WorkoutSet(
            workout=workout,
            exercise=exercise,
            logged_at=timezone.now(),
            duration_seconds=None,
        )

        with self.assertRaises(ValidationError):
            workout_set.full_clean()

    def test_timed_exercise_allows_missing_reps(self):
        workout = make_workout()
        exercise = make_exercise(
            name="Plank",
            category=Exercise.Category.TIMED,
        )
        workout_set = WorkoutSet(
            workout=workout,
            exercise=exercise,
            logged_at=timezone.now(),
            duration_seconds=60,
            reps=None,
        )

        workout_set.full_clean()


class WorkoutSetNumberingTests(TestCase):
    def test_next_set_number_starts_at_one(self):
        workout = make_workout()
        exercise = make_exercise()

        self.assertEqual(WorkoutSet.next_set_number(workout, exercise), 1)

    def test_next_set_number_increments_for_same_exercise(self):
        workout = make_workout()
        exercise = make_exercise()
        make_workout_set(workout, exercise, set_number=1)

        self.assertEqual(WorkoutSet.next_set_number(workout, exercise), 2)

    def test_save_assigns_incrementing_set_numbers(self):
        workout = make_workout()
        exercise = make_exercise()

        first = make_workout_set(workout, exercise, reps=5)
        second = make_workout_set(workout, exercise, reps=5)

        self.assertEqual(first.set_number, 1)
        self.assertEqual(second.set_number, 2)

    def test_full_clean_before_save_allows_second_set(self):
        """Reproduce: validate with default set_number=1 before save assigns next."""
        workout = make_workout()
        exercise = make_exercise()
        make_workout_set(workout, exercise, reps=5)

        second = WorkoutSet(
            workout=workout,
            exercise=exercise,
            logged_at=timezone.now(),
            weight=135,
            reps=5,
        )
        second.full_clean()
        second.save()

        self.assertEqual(second.set_number, 2)

    def test_save_does_not_renumber_existing_set(self):
        workout = make_workout()
        exercise = make_exercise()
        workout_set = make_workout_set(workout, exercise, reps=5)
        self.assertEqual(workout_set.set_number, 1)

        workout_set.reps = 6
        workout_set.save()
        workout_set.refresh_from_db()

        self.assertEqual(workout_set.set_number, 1)


class ExerciseRecencyOrderingTests(TestCase):
    def test_ordered_by_recency_puts_recent_exercises_first(self):
        user = make_user()
        workout = make_workout(user=user)
        alpha = make_exercise(name="Alpha")
        make_exercise(name="Beta")
        gamma = make_exercise(name="Gamma")

        now = timezone.now()
        make_workout_set(workout, gamma, logged_at=now - timedelta(minutes=1))
        make_workout_set(workout, alpha, logged_at=now - timedelta(minutes=2))

        ordered = Exercise.ordered_by_recency(user)
        ordered_names = [exercise.name for exercise in ordered]

        self.assertEqual(ordered_names[:2], ["Gamma", "Alpha"])
        self.assertIn("Beta", ordered_names)


class ExerciseLastWeightTests(TestCase):
    def test_last_weight_returns_none_without_history(self):
        user = make_user()
        exercise = make_exercise()

        self.assertIsNone(exercise.last_weight(user))

    def test_last_weight_ignores_null_weights(self):
        user = make_user()
        workout = make_workout(user=user)
        exercise = make_exercise(category=Exercise.Category.BODYWEIGHT)
        make_workout_set(workout, exercise, weight=None, reps=10)

        self.assertIsNone(exercise.last_weight(user))

    def test_last_weight_is_scoped_to_user(self):
        user = make_user("athlete")
        other = make_user("other")
        exercise = make_exercise()
        make_workout_set(make_workout(user=other), exercise, weight=315, reps=1)

        self.assertIsNone(exercise.last_weight(user))

    def test_last_weight_returns_most_recent(self):
        user = make_user()
        workout = make_workout(user=user)
        exercise = make_exercise()
        now = timezone.now()
        make_workout_set(
            workout, exercise, weight=135, reps=8, logged_at=now - timedelta(days=1)
        )
        make_workout_set(workout, exercise, weight=155, reps=5, logged_at=now)

        self.assertEqual(exercise.last_weight(user), Decimal("155.0"))
