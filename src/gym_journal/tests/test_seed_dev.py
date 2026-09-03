from django.core.management import call_command
from django.test import TestCase

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
