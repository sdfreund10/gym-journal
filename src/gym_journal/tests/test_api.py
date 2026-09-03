from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from gym_journal.models import Exercise, WorkoutSet
from gym_journal.tests.helpers import (
    make_exercise,
    make_muscle,
    make_user,
    make_workout,
    make_workout_set,
)


class ApiAuthMixin:
    def authenticate(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return token


class AuthApiTests(ApiAuthMixin, APITestCase):
    def setUp(self):
        self.user = make_user(username="athlete", password="secret-pass")

    def test_login_returns_token(self):
        response = self.client.post(
            reverse("api_login"),
            {"username": "athlete", "password": "secret-pass"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["username"], "athlete")
        self.assertTrue(Token.objects.filter(user=self.user).exists())

    def test_login_rejects_bad_password(self):
        response = self.client.post(
            reverse("api_login"),
            {"username": "athlete", "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_requests_return_401(self):
        response = self.client.get(reverse("api_summary"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_and_logout(self):
        token = self.authenticate(self.user)
        me = self.client.get(reverse("api_me"))
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["username"], "athlete")

        logout = self.client.post(reverse("api_logout"))
        self.assertEqual(logout.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Token.objects.filter(key=token.key).exists())

        after = self.client.get(reverse("api_me"))
        self.assertEqual(after.status_code, status.HTTP_401_UNAUTHORIZED)


class WorkoutApiTests(ApiAuthMixin, APITestCase):
    def setUp(self):
        self.user = make_user(username="athlete")
        self.other = make_user(username="other")
        self.exercise = make_exercise(name="Squat")
        self.timed = make_exercise(
            name="Plank",
            category=Exercise.Category.TIMED,
        )
        self.authenticate(self.user)

    def test_start_finish_and_list_workouts(self):
        start = self.client.post(reverse("api_start_workout"), format="json")
        self.assertEqual(start.status_code, status.HTTP_201_CREATED)
        workout_id = start.data["id"]

        active = self.client.get(reverse("api_active_workout"))
        self.assertEqual(active.status_code, status.HTTP_200_OK)
        self.assertEqual(active.data["id"], workout_id)

        finish = self.client.post(reverse("api_finish_workout"), format="json")
        self.assertEqual(finish.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(finish.data["ended_at"])

        listing = self.client.get(reverse("api_workout_list"))
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data["count"], 1)
        self.assertEqual(listing.data["results"][0]["id"], workout_id)

    def test_cannot_start_second_active_workout(self):
        self.client.post(reverse("api_start_workout"), format="json")
        again = self.client.post(reverse("api_start_workout"), format="json")
        self.assertEqual(again.status_code, status.HTTP_400_BAD_REQUEST)

    def test_log_and_delete_set(self):
        self.client.post(reverse("api_start_workout"), format="json")
        created = self.client.post(
            reverse("api_log_set"),
            {"exercise": self.exercise.id, "weight": "135.0", "reps": 5},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        set_id = created.data["id"]
        self.assertEqual(created.data["set_number"], 1)

        deleted = self.client.delete(reverse("api_delete_set", args=[set_id]))
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(WorkoutSet.objects.filter(pk=set_id).exists())

    def test_log_set_validation_for_timed_and_reps(self):
        self.client.post(reverse("api_start_workout"), format="json")

        missing_reps = self.client.post(
            reverse("api_log_set"),
            {"exercise": self.exercise.id, "weight": "100.0"},
            format="json",
        )
        self.assertEqual(missing_reps.status_code, status.HTTP_400_BAD_REQUEST)

        missing_duration = self.client.post(
            reverse("api_log_set"),
            {"exercise": self.timed.id},
            format="json",
        )
        self.assertEqual(missing_duration.status_code, status.HTTP_400_BAD_REQUEST)

        ok = self.client.post(
            reverse("api_log_set"),
            {"exercise": self.timed.id, "duration_seconds": 45},
            format="json",
        )
        self.assertEqual(ok.status_code, status.HTTP_201_CREATED)

    def test_cannot_access_other_users_workout_or_set(self):
        other_workout = make_workout(user=self.other)
        other_set = make_workout_set(other_workout, self.exercise)

        detail = self.client.get(
            reverse("api_workout_detail", args=[other_workout.id])
        )
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)

        deleted = self.client.delete(reverse("api_delete_set", args=[other_set.id]))
        self.assertEqual(deleted.status_code, status.HTTP_404_NOT_FOUND)

    def test_summary_reflects_active_workout(self):
        workout = make_workout(user=self.user)
        make_workout_set(workout, self.exercise)
        finished = make_workout(
            user=self.user,
            started_at=timezone.now(),
            ended_at=timezone.now(),
        )
        make_workout_set(finished, self.exercise)

        summary = self.client.get(reverse("api_summary"))
        self.assertEqual(summary.status_code, status.HTTP_200_OK)
        self.assertEqual(summary.data["active_workout_id"], workout.id)
        self.assertEqual(summary.data["today_set_count"], 1)
        self.assertEqual(summary.data["finished_workout_count"], 1)
        self.assertEqual(summary.data["last_workout"]["id"], finished.id)


class ExerciseApiTests(ApiAuthMixin, APITestCase):
    def setUp(self):
        self.user = make_user()
        self.muscle = make_muscle("Chest")
        self.authenticate(self.user)

    def test_muscle_list(self):
        response = self.client.get(reverse("api_muscle_list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Chest")

    def test_exercise_crud(self):
        created = self.client.post(
            reverse("api_exercise_list"),
            {
                "name": "Bench Press",
                "category": Exercise.Category.FREE_WEIGHT,
                "targeted_muscle_ids": [self.muscle.id],
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        exercise_id = created.data["id"]
        self.assertEqual(created.data["targeted_muscles"][0]["name"], "Chest")

        detail = self.client.get(reverse("api_exercise_detail", args=[exercise_id]))
        self.assertEqual(detail.status_code, status.HTTP_200_OK)

        patched = self.client.patch(
            reverse("api_exercise_detail", args=[exercise_id]),
            {"name": "Barbell Bench"},
            format="json",
        )
        self.assertEqual(patched.status_code, status.HTTP_200_OK)
        self.assertEqual(patched.data["name"], "Barbell Bench")

        deleted = self.client.delete(
            reverse("api_exercise_detail", args=[exercise_id])
        )
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Exercise.objects.filter(pk=exercise_id).exists())

    def test_exercise_list_includes_last_weight(self):
        exercise = make_exercise(name="Deadlift", muscles=[self.muscle])
        workout = make_workout(user=self.user, ended_at=timezone.now())
        make_workout_set(workout, exercise, weight=225, reps=3)

        response = self.client.get(reverse("api_exercise_list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data["results"][0]
        self.assertEqual(result["last_weight"], "225.0")
