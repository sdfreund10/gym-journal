from gym_journal.models import Exercise

MUSCLES = [
    "Chest",
    "Back",
    "Shoulders",
    "Biceps",
    "Triceps",
    "Quads",
    "Hamstrings",
    "Glutes",
    "Core",
]

EXERCISES = [
    {
        "name": "Bench Press",
        "category": Exercise.Category.FREE_WEIGHT,
        "muscles": ["Chest", "Triceps", "Shoulders"],
    },
    {
        "name": "Squat",
        "category": Exercise.Category.FREE_WEIGHT,
        "muscles": ["Quads", "Glutes", "Hamstrings"],
    },
    {
        "name": "Dumbbell Row",
        "category": Exercise.Category.DUMBBELL,
        "muscles": ["Back", "Biceps"],
    },
    {
        "name": "Plank",
        "category": Exercise.Category.TIMED,
        "muscles": ["Core"],
    },
]
