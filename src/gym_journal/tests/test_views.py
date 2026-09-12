from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from gym_journal.models import Exercise, Workout
from gym_journal.views import WORKOUT_TIMEOUT_LIMIT_MINUTES, close_inactive_workouts

from .helpers import (
    make_exercise,
    make_muscle,
    make_user,
    make_workout,
    make_workout_set,
)


@close_inactive_workouts
def _decorated_view(request):
    return "ok"


class AuthenticatedTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)


class AuthGateTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_anonymous_index_redirects_to_login(self):
        response = self.client.get(reverse("index"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('index')}",
        )

    def test_login_page_renders(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in")
        self.assertContains(response, "Exercise Tracker")


class IndexViewTests(AuthenticatedTestCase):
    def test_index_renders_successfully(self):
        response = self.client.get(reverse("index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Exercise Tracker")
        self.assertContains(response, "Sign out")

    def test_index_shows_library_counts(self):
        make_exercise(name="Squat")
        make_exercise(name="Bench Press")
        finished = make_workout(user=self.user, ended_at=timezone.now())
        make_workout_set(finished, make_exercise(name="Row"))

        response = self.client.get(reverse("index"))

        self.assertContains(response, "3 exercises")
        self.assertContains(response, "1 workout finished")

    def test_index_shows_resume_link_when_workout_is_active(self):
        make_workout(user=self.user)

        response = self.client.get(reverse("index"))

        self.assertContains(response, "Resume workout")

    def test_index_shows_start_button_when_no_active_workout(self):
        response = self.client.get(reverse("index"))

        self.assertContains(response, "Start workout")
        self.assertNotContains(response, "Resume workout")

    def test_index_ignores_other_users_workouts(self):
        other = make_user("other")
        make_workout(user=other)
        make_workout(user=other, ended_at=timezone.now())

        response = self.client.get(reverse("index"))

        self.assertContains(response, "Start workout")
        self.assertContains(response, "0 workouts finished")


class WorkoutDetailViewTests(AuthenticatedTestCase):
    def test_shows_no_active_page_when_no_workout(self):
        response = self.client.get(reverse("active_workout_detail"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No active workout.")
        self.assertContains(response, reverse("index"))

    def test_shows_active_workout_sets(self):
        workout = make_workout(user=self.user)
        exercise = make_exercise()
        make_workout_set(workout, exercise, reps=10, weight=135)

        response = self.client.get(reverse("active_workout_detail"))

        self.assertRedirects(
            response,
            reverse("workout_detail", kwargs={"workout_id": workout.id}),
        )
        detail = self.client.get(
            reverse("workout_detail", kwargs={"workout_id": workout.id})
        )
        self.assertContains(detail, exercise.name)

    def test_workout_detail_404_for_other_users_workout(self):
        other = make_user("other")
        workout = make_workout(user=other)

        response = self.client.get(
            reverse("workout_detail", kwargs={"workout_id": workout.id})
        )

        self.assertEqual(response.status_code, 404)

    def test_finished_workout_detail_is_read_only(self):
        workout = make_workout(user=self.user, ended_at=timezone.now())
        exercise = make_exercise()
        make_workout_set(workout, exercise)

        response = self.client.get(
            reverse("workout_detail", kwargs={"workout_id": workout.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Completed")
        self.assertNotContains(response, reverse("finish_workout"))
        self.assertNotContains(response, "Add Exercise")
        self.assertNotContains(response, 'aria-label="Delete set"')

    def test_finished_workout_detail_links_back_to_history(self):
        workout = make_workout(user=self.user, ended_at=timezone.now())

        response = self.client.get(
            reverse("workout_detail", kwargs={"workout_id": workout.id}),
            {"from": "history"},
        )

        self.assertContains(response, reverse("workout_history"))
        self.assertContains(response, "History")


class WorkoutPickExerciseViewTests(AuthenticatedTestCase):
    def test_shows_no_active_page_when_no_workout(self):
        response = self.client.get(reverse("workout_pick_exercise"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No active workout.")

    def test_lists_exercises_when_workout_is_active(self):
        make_workout(user=self.user)
        make_exercise(name="Deadlift")

        response = self.client.get(reverse("workout_pick_exercise"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Deadlift")

    def test_picker_links_to_new_exercise_during_active_workout(self):
        make_workout(user=self.user)

        response = self.client.get(reverse("workout_pick_exercise"))

        self.assertContains(response, reverse("exercise_new"))
        self.assertContains(response, "from=workout")


class WorkoutLogSetViewTests(AuthenticatedTestCase):
    def test_shows_no_active_page_when_no_workout(self):
        exercise = make_exercise()

        response = self.client.get(
            reverse("workout_log_set", kwargs={"exercise_id": exercise.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No active workout.")

    def test_renders_log_form_for_active_workout(self):
        make_workout(user=self.user)
        exercise = make_exercise(name="Overhead Press")

        response = self.client.get(
            reverse("workout_log_set", kwargs={"exercise_id": exercise.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Overhead Press")
        self.assertContains(response, "Set 1")

    def test_next_set_number_increments_for_repeat_exercise(self):
        workout = make_workout(user=self.user)
        exercise = make_exercise()
        make_workout_set(workout, exercise, set_number=1)

        response = self.client.get(
            reverse("workout_log_set", kwargs={"exercise_id": exercise.pk})
        )

        self.assertContains(response, "Set 2")


class StartWorkoutViewTests(AuthenticatedTestCase):
    def test_start_workout_creates_active_workout_and_redirects(self):
        response = self.client.post(reverse("start_workout"))

        active = Workout.objects.for_user(self.user).active()
        self.assertEqual(active.count(), 1)
        self.assertRedirects(
            response,
            reverse("workout_detail", kwargs={"workout_id": active.first().id}),
        )

    def test_start_workout_does_not_create_second_active_workout(self):
        make_workout(user=self.user)

        response = self.client.post(reverse("start_workout"), follow=True)

        self.assertEqual(Workout.objects.for_user(self.user).active().count(), 1)
        self.assertRedirects(response, reverse("index"))
        self.assertContains(response, "You already have a workout in progress.")


class LogSetViewTests(AuthenticatedTestCase):
    def test_log_set_redirects_to_workout_summary(self):
        workout = make_workout(user=self.user)
        exercise = make_exercise(category=Exercise.Category.FREE_WEIGHT)

        response = self.client.post(
            reverse("log_set", kwargs={"exercise_id": exercise.pk}),
            data={"weight": "135", "reps": "8"},
        )

        self.assertRedirects(
            response,
            reverse("workout_detail", kwargs={"workout_id": workout.id}),
        )
        self.assertEqual(workout.workoutset_set.count(), 1)

    def test_log_second_set_of_same_exercise(self):
        workout = make_workout(user=self.user)
        exercise = make_exercise(category=Exercise.Category.FREE_WEIGHT)
        make_workout_set(workout, exercise, weight=135, reps=8)

        response = self.client.post(
            reverse("log_set", kwargs={"exercise_id": exercise.pk}),
            data={"weight": "135", "reps": "8"},
            follow=True,
        )

        self.assertContains(response, "Set logged.")
        self.assertEqual(workout.workoutset_set.count(), 2)
        self.assertEqual(
            list(
                workout.workoutset_set.order_by("set_number").values_list(
                    "set_number", flat=True
                )
            ),
            [1, 2],
        )

    def test_log_set_shows_success_on_workout_page(self):
        workout = make_workout(user=self.user)
        exercise = make_exercise(category=Exercise.Category.FREE_WEIGHT)

        response = self.client.post(
            reverse("log_set", kwargs={"exercise_id": exercise.pk}),
            data={"weight": "135", "reps": "8"},
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("workout_detail", kwargs={"workout_id": workout.id}),
        )
        self.assertContains(response, "Set logged.")

    def test_log_set_redirects_home_when_no_active_workout(self):
        exercise = make_exercise()

        response = self.client.post(
            reverse("log_set", kwargs={"exercise_id": exercise.pk}),
            data={"weight": "135", "reps": "8"},
            follow=True,
        )

        self.assertRedirects(response, reverse("index"))
        self.assertContains(response, "Start a workout before logging sets.")

    def test_log_set_shows_error_when_reps_missing(self):
        workout = make_workout(user=self.user)
        exercise = make_exercise(category=Exercise.Category.FREE_WEIGHT)

        response = self.client.post(
            reverse("log_set", kwargs={"exercise_id": exercise.pk}),
            data={"weight": "135"},
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("workout_log_set", kwargs={"exercise_id": exercise.pk}),
        )
        self.assertContains(response, "Reps must be set of non-timed exercises.")
        self.assertEqual(workout.workoutset_set.count(), 0)


class DeleteSetViewTests(AuthenticatedTestCase):
    def test_delete_set_removes_owned_set_and_redirects(self):
        workout = make_workout(user=self.user)
        exercise = make_exercise()
        workout_set = make_workout_set(workout, exercise)

        response = self.client.post(
            reverse("delete_set", kwargs={"set_id": workout_set.pk}),
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("workout_detail", kwargs={"workout_id": workout.id}),
        )
        self.assertContains(response, "Set removed.")
        self.assertFalse(workout.workoutset_set.filter(pk=workout_set.pk).exists())

    def test_delete_set_blocked_on_finished_workout(self):
        workout = make_workout(user=self.user, ended_at=timezone.now())
        exercise = make_exercise()
        workout_set = make_workout_set(workout, exercise)

        response = self.client.post(
            reverse("delete_set", kwargs={"set_id": workout_set.pk}),
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("workout_detail", kwargs={"workout_id": workout.id}),
        )
        self.assertContains(response, "Cannot modify a finished workout.")
        self.assertTrue(workout.workoutset_set.filter(pk=workout_set.pk).exists())

    def test_delete_set_404_for_other_users_set(self):
        other = make_user("other")
        workout = make_workout(user=other)
        exercise = make_exercise()
        workout_set = make_workout_set(workout, exercise)

        response = self.client.post(
            reverse("delete_set", kwargs={"set_id": workout_set.pk})
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(workout.workoutset_set.filter(pk=workout_set.pk).exists())


class WorkoutHistoryViewTests(AuthenticatedTestCase):
    def test_workout_history_lists_finished_workouts(self):
        finished = make_workout(user=self.user, ended_at=timezone.now())
        make_workout_set(finished, make_exercise())
        active = make_workout(user=self.user)

        response = self.client.get(reverse("workout_history"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "History")
        self.assertContains(
            response, reverse("workout_detail", kwargs={"workout_id": finished.id})
        )
        self.assertContains(response, "1 set")
        self.assertNotContains(
            response,
            reverse("workout_detail", kwargs={"workout_id": active.id}),
        )

    def test_workout_history_excludes_other_users_workouts(self):
        finished = make_workout(user=self.user, ended_at=timezone.now())
        other_finished = make_workout(user=make_user("other"), ended_at=timezone.now())

        response = self.client.get(reverse("workout_history"))

        self.assertContains(
            response, reverse("workout_detail", kwargs={"workout_id": finished.id})
        )
        self.assertNotContains(
            response,
            reverse("workout_detail", kwargs={"workout_id": other_finished.id}),
        )

    def test_index_links_last_session_to_workout_detail(self):
        finished = make_workout(user=self.user, ended_at=timezone.now())
        make_workout_set(finished, make_exercise())

        response = self.client.get(reverse("index"))

        self.assertContains(response, "Last session")
        self.assertContains(response, reverse("workout_history"))
        self.assertContains(
            response,
            reverse("workout_detail", kwargs={"workout_id": finished.id}),
        )


class FinishWorkoutViewTests(AuthenticatedTestCase):
    def test_finish_workout_marks_workout_complete_and_redirects(self):
        workout = make_workout(user=self.user)

        response = self.client.post(reverse("finish_workout"))

        workout.refresh_from_db()
        self.assertIsNotNone(workout.ended_at)
        self.assertRedirects(response, reverse("index"))

    def test_finish_workout_when_none_active_shows_index_with_error(self):
        response = self.client.post(reverse("finish_workout"), follow=True)

        self.assertRedirects(response, reverse("index"))
        self.assertContains(response, "No active workout to finish.")


class ExerciseLibraryViewTests(AuthenticatedTestCase):
    def test_exercise_list_shows_exercises_and_muscles(self):
        chest = make_muscle("Chest")
        make_exercise(name="Bench Press", muscles=[chest])

        response = self.client.get(reverse("exercise_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bench Press")
        self.assertContains(response, "Chest")

    def test_exercise_new_renders_create_form(self):
        response = self.client.get(reverse("exercise_new"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New exercise")

    def test_exercise_detail_shows_exercise(self):
        exercise = make_exercise(name="Romanian Deadlift")

        response = self.client.get(
            reverse("exercise_detail", kwargs={"exercise_id": exercise.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Romanian Deadlift")

    def test_exercise_detail_hides_delete_when_sets_exist(self):
        exercise = make_exercise(name="Squat")
        make_workout_set(make_workout(user=self.user), exercise)

        response = self.client.get(
            reverse("exercise_detail", kwargs={"exercise_id": exercise.pk})
        )

        self.assertContains(response, "Exercises with logged sets cannot be deleted.")
        self.assertContains(response, "You have 1 set recorded")
        self.assertNotContains(response, 'data-toggle="delete-confirm"')

    def test_exercise_detail_hides_delete_when_other_users_have_sets(self):
        exercise = make_exercise(name="Squat")
        other = make_user("other-lifter")
        make_workout_set(make_workout(user=other), exercise)

        response = self.client.get(
            reverse("exercise_detail", kwargs={"exercise_id": exercise.pk})
        )

        self.assertContains(response, "Exercises with logged sets cannot be deleted.")
        self.assertContains(response, "Other athletes have 1 set recorded")
        self.assertNotContains(response, 'data-toggle="delete-confirm"')

    def test_exercise_detail_shows_not_found_for_missing_exercise(self):
        response = self.client.get(
            reverse("exercise_detail", kwargs={"exercise_id": 999})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This exercise no longer exists.")

    def test_exercise_edit_renders_form_with_existing_values(self):
        chest = make_muscle("Chest")
        exercise = make_exercise(name="Flyes", muscles=[chest])

        response = self.client.get(
            reverse("exercise_edit", kwargs={"exercise_id": exercise.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Flyes")
        self.assertContains(response, "Chest")

    def test_create_exercise_adds_to_library(self):
        chest = make_muscle("Chest")

        response = self.client.post(
            reverse("exercise_create"),
            data={
                "name": "Cable Fly",
                "category": Exercise.Category.MACHINE,
                "targeted_muscles": [str(chest.pk)],
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("exercise_list"))
        self.assertContains(response, "Exercise added.")
        self.assertTrue(Exercise.objects.filter(name="Cable Fly").exists())
        exercise = Exercise.objects.get(name="Cable Fly")
        self.assertEqual(list(exercise.targeted_muscles.all()), [chest])

    def test_create_exercise_during_active_workout_returns_to_log_set(self):
        make_workout(user=self.user)
        chest = make_muscle("Chest")

        response = self.client.post(
            reverse("exercise_create"),
            data={
                "name": "Cable Fly",
                "category": Exercise.Category.MACHINE,
                "targeted_muscles": [str(chest.pk)],
                "from": "workout",
            },
            follow=True,
        )

        exercise = Exercise.objects.get(name="Cable Fly")
        self.assertRedirects(
            response,
            reverse("workout_log_set", kwargs={"exercise_id": exercise.pk}),
        )
        self.assertContains(response, "Cable Fly")
        self.assertContains(response, "Set 1")

    def test_create_exercise_shows_error_for_duplicate_name(self):
        make_exercise(name="Bench Press")

        response = self.client.post(
            reverse("exercise_create"),
            data={
                "name": "Bench Press",
                "category": Exercise.Category.FREE_WEIGHT,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New exercise")
        self.assertContains(response, "already exists")

    def test_update_exercise_saves_changes_and_redirects(self):
        chest = make_muscle("Chest")
        back = make_muscle("Back")
        exercise = make_exercise(
            name="Flyes",
            category=Exercise.Category.DUMBBELL,
            muscles=[chest],
        )

        response = self.client.post(
            reverse("exercise_update", kwargs={"exercise_id": exercise.pk}),
            data={
                "name": "Cable Row",
                "category": Exercise.Category.MACHINE,
                "targeted_muscles": [str(back.pk)],
            },
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("exercise_detail", kwargs={"exercise_id": exercise.pk}),
        )
        self.assertContains(response, "Exercise saved.")
        exercise.refresh_from_db()
        self.assertEqual(exercise.name, "Cable Row")
        self.assertEqual(exercise.category, Exercise.Category.MACHINE)
        self.assertEqual(list(exercise.targeted_muscles.all()), [back])

    def test_delete_exercise_removes_exercise_and_redirects(self):
        exercise = make_exercise(name="Skull Crushers")

        response = self.client.post(
            reverse("exercise_delete", kwargs={"exercise_id": exercise.pk}),
            follow=True,
        )

        self.assertRedirects(response, reverse("exercise_list"))
        self.assertContains(response, "Exercise deleted.")
        self.assertFalse(Exercise.objects.filter(pk=exercise.pk).exists())

    def test_delete_exercise_blocked_when_sets_exist(self):
        exercise = make_exercise(name="Skull Crushers")
        make_workout_set(make_workout(user=self.user), exercise)

        response = self.client.post(
            reverse("exercise_delete", kwargs={"exercise_id": exercise.pk}),
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("exercise_detail", kwargs={"exercise_id": exercise.pk}),
        )
        self.assertContains(response, "Cannot delete an exercise with logged sets.")
        self.assertTrue(Exercise.objects.filter(pk=exercise.pk).exists())

    def test_delete_exercise_blocked_when_other_users_have_sets(self):
        exercise = make_exercise(name="Skull Crushers")
        make_workout_set(make_workout(user=make_user("other-lifter")), exercise)

        response = self.client.post(
            reverse("exercise_delete", kwargs={"exercise_id": exercise.pk}),
            follow=True,
        )

        self.assertContains(response, "Cannot delete an exercise with logged sets.")
        self.assertTrue(Exercise.objects.filter(pk=exercise.pk).exists())


class CloseInactiveWorkoutsDecoratorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = make_user()
        self.exercise = make_exercise()

    def _authenticated_request(self):
        request = self.factory.get("/")
        request.user = self.user
        return request

    def test_closes_stale_active_workout_with_no_sets(self):
        stale = make_workout(
            user=self.user,
            started_at=timezone.now()
            - timedelta(minutes=WORKOUT_TIMEOUT_LIMIT_MINUTES + 1),
        )

        self.assertEqual(_decorated_view(self._authenticated_request()), "ok")

        stale.refresh_from_db()
        self.assertEqual(stale.ended_at, stale.started_at)

    def test_keeps_recent_active_workout(self):
        recent = make_workout(user=self.user, started_at=timezone.now())

        _decorated_view(self._authenticated_request())

        recent.refresh_from_db()
        self.assertIsNone(recent.ended_at)

    def test_closes_when_last_set_is_stale(self):
        workout = make_workout(
            user=self.user,
            started_at=timezone.now()
            - timedelta(minutes=WORKOUT_TIMEOUT_LIMIT_MINUTES + 10),
        )
        make_workout_set(
            workout=workout,
            exercise=self.exercise,
            logged_at=timezone.now()
            - timedelta(minutes=WORKOUT_TIMEOUT_LIMIT_MINUTES + 1),
        )

        _decorated_view(self._authenticated_request())

        workout.refresh_from_db()
        self.assertIsNotNone(workout.ended_at)

    def test_keeps_when_last_set_is_recent(self):
        workout = make_workout(
            user=self.user,
            started_at=timezone.now()
            - timedelta(minutes=WORKOUT_TIMEOUT_LIMIT_MINUTES + 10),
        )
        make_workout_set(
            workout=workout,
            exercise=self.exercise,
            logged_at=timezone.now(),
        )

        _decorated_view(self._authenticated_request())

        workout.refresh_from_db()
        self.assertIsNone(workout.ended_at)

    def test_does_not_touch_other_users_workouts(self):
        other = make_user("other")
        other_workout = make_workout(
            user=other,
            started_at=timezone.now()
            - timedelta(minutes=WORKOUT_TIMEOUT_LIMIT_MINUTES + 1),
        )

        _decorated_view(self._authenticated_request())

        other_workout.refresh_from_db()
        self.assertIsNone(other_workout.ended_at)

    def test_skips_anonymous_users(self):
        stale = make_workout(
            user=self.user,
            started_at=timezone.now()
            - timedelta(minutes=WORKOUT_TIMEOUT_LIMIT_MINUTES + 1),
        )
        request = self.factory.get("/")
        request.user = AnonymousUser()

        self.assertEqual(_decorated_view(request), "ok")

        stale.refresh_from_db()
        self.assertIsNone(stale.ended_at)

    def test_leaves_already_finished_workouts_alone(self):
        ended_at = timezone.now() - timedelta(hours=1)
        finished = make_workout(
            user=self.user,
            started_at=timezone.now()
            - timedelta(minutes=WORKOUT_TIMEOUT_LIMIT_MINUTES + 10),
            ended_at=ended_at,
        )

        _decorated_view(self._authenticated_request())

        finished.refresh_from_db()
        self.assertEqual(finished.ended_at, ended_at)
