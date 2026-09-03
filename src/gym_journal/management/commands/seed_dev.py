from django.core.management.base import BaseCommand

from gym_journal.models import Exercise, Muscle
from gym_journal.seed_data import EXERCISES, MUSCLES


class Command(BaseCommand):
    help = "Seed development data: muscle groups and common exercises."

    def handle(self, *args, **options):
        muscles_by_name = {}
        muscles_created = 0

        for name in MUSCLES:
            muscle, created = Muscle.objects.get_or_create(name=name)
            muscles_by_name[name] = muscle
            if created:
                muscles_created += 1
                self.stdout.write(f"  + muscle: {name}")
            else:
                self.stdout.write(f"  = muscle: {name} (exists)")

        exercises_created = 0
        for spec in EXERCISES:
            exercise, created = Exercise.objects.get_or_create(
                name=spec["name"],
                defaults={"category": spec["category"]},
            )
            if created:
                exercises_created += 1
                self.stdout.write(f"  + exercise: {spec['name']}")
            else:
                self.stdout.write(f"  = exercise: {spec['name']} (exists)")

            exercise.targeted_muscles.set(
                [muscles_by_name[name] for name in spec["muscles"]]
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created {muscles_created} muscle(s) and "
                f"{exercises_created} exercise(s)."
            )
        )
