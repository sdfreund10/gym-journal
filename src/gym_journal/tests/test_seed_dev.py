from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

from gym_journal.management.commands.seed_dev import DEV_PASSWORD, DEV_USERNAME
from gym_journal.models import Exercise, Muscle
from gym_journal.seed_data import EXERCISES, MUSCLES


class SeedDevCommandTests(TestCase):
    def test_seed_dev_creates_muscles_and_exercises(self):
        call_command("seed_dev", verbosity=0)

        self.assertEqual(Muscle.objects.count(), len(MUSCLES))
        self.assertEqual(Exercise.objects.count(), len(EXERCISES))

        bench = Exercise.objects.get(name="Bench Press")
        self.assertEqual(bench.category, Exercise.Category.FREE_WEIGHT)
        self.assertCountEqual(
            bench.targeted_muscles.values_list("name", flat=True),
            ["Chest", "Triceps", "Shoulders"],
        )

        plank = Exercise.objects.get(name="Plank")
        self.assertEqual(plank.category, Exercise.Category.TIMED)
        self.assertCountEqual(
            plank.targeted_muscles.values_list("name", flat=True),
            ["Core"],
        )

    def test_seed_dev_is_idempotent(self):
        call_command("seed_dev", verbosity=0)
        call_command("seed_dev", verbosity=0)

        self.assertEqual(Muscle.objects.count(), len(MUSCLES))
        self.assertEqual(Exercise.objects.count(), len(EXERCISES))

    @override_settings(DEBUG=True)
    def test_seed_dev_creates_dev_user_when_debug_is_on(self):
        call_command("seed_dev", verbosity=0)
        call_command("seed_dev", verbosity=0)

        user = get_user_model().objects.get(username=DEV_USERNAME)
        self.assertTrue(user.check_password(DEV_PASSWORD))
        self.assertFalse(user.is_staff)
        self.assertEqual(
            get_user_model().objects.filter(username=DEV_USERNAME).count(), 1
        )

    @override_settings(DEBUG=False)
    def test_seed_dev_skips_user_when_debug_is_off(self):
        call_command("seed_dev", verbosity=0)

        self.assertFalse(
            get_user_model().objects.filter(username=DEV_USERNAME).exists()
        )
        self.assertEqual(Muscle.objects.count(), len(MUSCLES))
