from datetime import timedelta

from django.core.cache import cache
from django.template.defaultfilters import date as date_filter
from django.template.loader import render_to_string
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from gym_journal.views import _rest_timer_context

from .helpers import make_exercise, make_user, make_workout, make_workout_set


class _AuthenticatedTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)


def _render_page_nav(*, is_active, last_set_logged_at, user=None):
    request = RequestFactory().get("/")
    request.user = user
    return render_to_string(
        "gym_journal/partials/page_nav.html",
        {
            "back_url": "/",
            "back_label": "Home",
            "is_active": is_active,
            "last_set_logged_at": last_set_logged_at,
            "user": user,
        },
        request=request,
    )


class RestTimerNavTests(_AuthenticatedTestCase):
    def test_nav_renders_timer_when_active_with_a_last_set(self):
        logged_at = timezone.now()
        html = _render_page_nav(
            is_active=True, last_set_logged_at=logged_at, user=self.user
        )

        self.assertIn("data-rest-timer", html)
        self.assertIn(f'data-rest-since="{date_filter(logged_at, "c")}"', html)
        self.assertIn("rest_timer.js", html)

    def test_nav_omits_timer_when_inactive_or_missing_last_set(self):
        logged_at = timezone.now()
        cases = (
            {"is_active": False, "last_set_logged_at": logged_at},
            {"is_active": True, "last_set_logged_at": None},
        )

        for context in cases:
            with self.subTest(**context):
                html = _render_page_nav(user=self.user, **context)
                self.assertNotIn("data-rest-timer", html)
                self.assertNotIn("rest_timer.js", html)


class RestTimerContextTests(_AuthenticatedTestCase):
    def test_inactive_when_workout_is_missing_or_finished(self):
        self.assertEqual(
            _rest_timer_context(None),
            {"is_active": False, "last_set_logged_at": None},
        )

        finished = make_workout(user=self.user, ended_at=timezone.now())
        make_workout_set(finished, make_exercise())

        self.assertEqual(
            _rest_timer_context(finished),
            {"is_active": False, "last_set_logged_at": None},
        )

    def test_uses_latest_set_on_an_active_workout(self):
        workout = make_workout(user=self.user)
        self.assertEqual(
            _rest_timer_context(workout),
            {"is_active": True, "last_set_logged_at": None},
        )

        now = timezone.now()
        make_workout_set(
            workout, make_exercise(name="Squat"), logged_at=now - timedelta(minutes=5)
        )
        latest = make_workout_set(
            workout, make_exercise(name="Row"), logged_at=now - timedelta(minutes=1)
        )

        self.assertEqual(
            _rest_timer_context(workout),
            {"is_active": True, "last_set_logged_at": latest.logged_at},
        )


class RestTimerPageWiringTests(_AuthenticatedTestCase):
    def setUp(self):
        super().setUp()
        self.workout = make_workout(user=self.user)
        older = make_exercise(name="Squat")
        self.exercise = make_exercise(name="Row")
        now = timezone.now()
        make_workout_set(self.workout, older, logged_at=now - timedelta(minutes=5))
        self.latest = make_workout_set(
            self.workout, self.exercise, logged_at=now - timedelta(minutes=1)
        )

    def test_in_workout_pages_pass_latest_set_to_nav(self):
        urls = (
            reverse("workout_detail", kwargs={"workout_id": self.workout.id}),
            reverse("workout_pick_exercise"),
            reverse("workout_log_set", kwargs={"exercise_id": self.exercise.pk}),
            reverse("edit_set", kwargs={"set_id": self.latest.pk}),
            f"{reverse('exercise_new')}?from=workout",
        )

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["is_active"])
                self.assertEqual(
                    response.context["last_set_logged_at"], self.latest.logged_at
                )

    def test_new_exercise_outside_workout_omits_timer_context(self):
        response = self.client.get(reverse("exercise_new"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context.get("is_active"))
        self.assertIsNone(response.context.get("last_set_logged_at"))
