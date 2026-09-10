from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from gym_journal.models import Exercise, Workout

from .helpers import make_exercise, make_muscle, make_user, make_workout, make_workout_set


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

    def test_shows_active_workout_sets(self):
        workout = make_workout(user=self.user)
        exercise = make_exercise()
        make_workout_set(workout, exercise, reps=10, weight=135)

        response = self.client.get(reverse("active_workout_detail"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, exercise.name)

    def test_workout_detail_404_for_other_users_workout(self):
        other = make_user("other")
        workout = make_workout(user=other)

        response = self.client.get(
            reverse("workout_detail", kwargs={"workout_id": workout.id})
        )

        self.assertEqual(response.status_code, 404)


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
    def test_log_set_redirects_to_workout_detail(self):
        workout = make_workout(user=self.user)
        exercise = make_exercise(category=Exercise.Category.FREE_WEIGHT)

        response = self.client.post(
            reverse("log_set", kwargs={"exercise_id": exercise.pk}),
            data={"weight": "135", "reps": "8"},
        )

        self.assertRedirects(response, reverse("workout_detail", kwargs={"workout_id": workout.id}))
        self.assertEqual(workout.workoutset_set.count(), 1)

    def test_log_second_set_of_same_exercise(self):
        workout = make_workout(user=self.user)
        exercise = make_exercise(category=Exercise.Category.FREE_WEIGHT)
        make_workout_set(workout, exercise, weight=135, reps=8)

        response = self.client.post(
            reverse("log_set", kwargs={"exercise_id": exercise.pk}),
            data={"weight": "135", "reps": "8", "action": "close"},
            follow=True,
        )

        self.assertContains(response, "Set logged.")
        self.assertEqual(workout.workoutset_set.count(), 2)
        self.assertEqual(
            list(workout.workoutset_set.order_by("set_number").values_list("set_number", flat=True)),
            [1, 2],
        )

    def test_log_set_action_log_stays_on_form_for_next_set(self):
        make_workout(user=self.user)
        exercise = make_exercise(category=Exercise.Category.FREE_WEIGHT)

        response = self.client.post(
            reverse("log_set", kwargs={"exercise_id": exercise.pk}),
            data={"weight": "135", "reps": "8", "action": "log"},
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("workout_log_set", kwargs={"exercise_id": exercise.pk}),
        )
        self.assertContains(response, "Set 2")

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

        self.assertRedirects(response, reverse("active_workout_detail"))
        self.assertContains(response, "Set removed.")
        self.assertFalse(
            workout.workoutset_set.filter(pk=workout_set.pk).exists()
        )

    def test_delete_set_404_for_other_users_set(self):
        other = make_user("other")
        workout = make_workout(user=other)
        exercise = make_exercise()
        workout_set = make_workout_set(workout, exercise)

        response = self.client.post(
            reverse("delete_set", kwargs={"set_id": workout_set.pk})
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            workout.workoutset_set.filter(pk=workout_set.pk).exists()
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
