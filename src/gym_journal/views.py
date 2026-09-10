from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Exercise, Muscle, Workout, WorkoutSet


def _validation_message(exc):
    if hasattr(exc, "message_dict"):
        non_field_errors = exc.message_dict.get("__all__")
        if non_field_errors:
            return str(non_field_errors[0])
        for field_errors in exc.message_dict.values():
            if field_errors:
                return str(field_errors[0])
    if exc.messages:
        return str(exc.messages[0])
    return "Something went wrong. Please try again."


def _optional_post_value(post, key):
    value = post.get(key)
    return value if value not in (None, "") else None


# Maybe Category should be an object - then each category could define its own defaults.
def _category_defaults(category):
    has_weight = category in {
        Exercise.Category.DUMBBELL,
        Exercise.Category.FREE_WEIGHT,
        Exercise.Category.MACHINE,
    }
    is_timed = category == Exercise.Category.TIMED
    default_weight = 45 if category == Exercise.Category.FREE_WEIGHT else 25
    return {
        "has_weight": has_weight,
        "is_timed": is_timed,
        "default_weight": default_weight,
        "default_reps": 8,
        "default_duration": 30,
    }


# GET /
@login_required
def index(request):
    user_workouts = Workout.objects.for_user(request.user)
    active_workout = user_workouts.active().first()
    active_set_count = 0
    if active_workout:
        active_set_count = active_workout.workoutset_set.count()

    last_workout = (
        user_workouts.filter(ended_at__isnull=False).order_by("-started_at").first()
    )
    last_workout_set_count = 0
    if last_workout:
        last_workout_set_count = last_workout.workoutset_set.count()

    return render(
        request,
        "gym_journal/index.html",
        {
            "active_workout": active_workout,
            "exercise_count": Exercise.objects.count(),
            "finished_workout_count": user_workouts.filter(
                ended_at__isnull=False
            ).count(),
            "active_set_count": active_set_count,
            "last_workout": last_workout,
            "last_workout_set_count": last_workout_set_count,
        },
    )


def _workout_detail_context(workout, request):
    sets = list(
        workout.workoutset_set.select_related("exercise").order_by("-logged_at")
    )
    if request.GET.get("from") == "history":
        back_url = reverse("workout_history")
        back_label = "History"
    else:
        back_url = reverse("index")
        back_label = "Home"
    return {
        "workout": workout,
        "sets": sets,
        "set_count": len(sets),
        "is_active": workout.ended_at is None,
        "back_url": back_url,
        "back_label": back_label,
    }


# GET /workout/
@login_required
def active_workout_detail(request):
    workout = Workout.objects.for_user(request.user).active().first()
    if not workout:
        return render(request, "gym_journal/workout/no_active.html")

    return redirect("workout_detail", workout_id=workout.id)


# GET /workout/:workout_id/
@login_required
def workout_detail(request, workout_id):
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)
    return render(
        request,
        "gym_journal/workout/detail.html",
        _workout_detail_context(workout, request),
    )


# GET /workouts/
@login_required
def workout_history(request):
    workouts = (
        Workout.objects.for_user(request.user)
        .filter(ended_at__isnull=False)
        .annotate(set_count=Count("workoutset"))
        .order_by("-started_at")
    )
    page_obj = Paginator(workouts, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "gym_journal/workout/history.html",
        {"page_obj": page_obj},
    )


# GET /workout/add/
@login_required
def workout_pick_exercise(request):
    active_workout = Workout.objects.for_user(request.user).active().first()
    if not active_workout:
        return render(request, "gym_journal/workout/no_active.html")

    exercises = Exercise.ordered_by_recency(request.user)
    recent_ids = WorkoutSet.recent_ids(request.user, limit=3)

    return render(
        request,
        "gym_journal/workout/pick_exercise.html",
        {
            "active_workout": active_workout,
            "exercises": exercises,
            "recent_exercise_ids": set(recent_ids),
        },
    )


def _from_active_workout(request):
    if request.POST.get("from") == "workout" or request.GET.get("from") == "workout":
        return Workout.objects.for_user(request.user).active().first() is not None
    return False


# GET /workout/add/<exercise_id>/
@login_required
def workout_log_set(request, exercise_id):
    workout = Workout.objects.for_user(request.user).active().first()
    if not workout:
        return render(request, "gym_journal/workout/no_active.html")

    exercise = get_object_or_404(Exercise, pk=exercise_id)
    next_set_number = WorkoutSet.next_set_number(workout, exercise)

    defaults = _category_defaults(exercise.category)
    return render(
        request,
        "gym_journal/workout/log_set.html",
        {
            "workout": workout,
            "exercise": exercise,
            "next_set_number": next_set_number,
            "last_weight": exercise.last_weight(request.user),
            **defaults,
        },
    )


# POST /workouts/start
# Create a new workout
@login_required
@require_POST
def start_workout(request):
    active_workout = Workout.objects.for_user(request.user).active().first()
    if active_workout:
        messages.error(request, "You already have a workout in progress.")
        return redirect("index")

    new_workout = Workout.start(request.user)
    messages.success(request, "Workout started.")
    return redirect("workout_detail", workout_id=new_workout.id)


# POST /workouts/finish
# Finish lastest active workout
@login_required
@require_POST
def finish_workout(request):
    active_workout = Workout.objects.for_user(request.user).active().first()
    if not active_workout:
        messages.error(request, "No active workout to finish.")
        return redirect("index")

    active_workout.ended_at = timezone.now()
    try:
        active_workout.full_clean()
        active_workout.save()
        messages.success(request, "Workout finished.")
        return redirect("index")
    except ValidationError as e:
        messages.error(request, _validation_message(e))
        return redirect("workout_detail", workout_id=active_workout.id)


# POST /workout/log/:exercise_id
# Log a set
@login_required
@require_POST
def log_set(request, exercise_id):
    active_workout = Workout.objects.for_user(request.user).active().first()
    if not active_workout:
        messages.error(request, "Start a workout before logging sets.")
        return redirect("index")

    exercise = get_object_or_404(Exercise, pk=exercise_id)

    new_set = WorkoutSet(
        workout=active_workout,
        exercise=exercise,
        logged_at=timezone.now(),
        weight=_optional_post_value(request.POST, "weight"),
        reps=_optional_post_value(request.POST, "reps"),
        duration_seconds=_optional_post_value(request.POST, "duration_seconds"),
    )

    try:
        new_set.full_clean()
        new_set.save()
        messages.success(request, "Set logged.")
        return redirect("workout_detail", workout_id=active_workout.id)
    except ValidationError as e:
        messages.error(request, _validation_message(e))
        return redirect("workout_log_set", exercise_id=exercise_id)


# POST /workout/set/<set_id>/delete/
@login_required
@require_POST
def delete_set(request, set_id):
    workout_set = get_object_or_404(
        WorkoutSet, pk=set_id, workout__user=request.user
    )
    workout = workout_set.workout
    if workout.ended_at is not None:
        messages.error(request, "Cannot modify a finished workout.")
        return redirect("workout_detail", workout_id=workout.id)

    workout_set.delete()
    messages.success(request, "Set removed.")
    return redirect("workout_detail", workout_id=workout.id)


# GET /exercises
@login_required
def exercise_list(request):
    exercises = Exercise.objects.prefetch_related("targeted_muscles").order_by("name")
    return render(
        request,
        "gym_journal/library/list.html",
        {
            "exercises": exercises,
            "muscles": Muscle.objects.order_by("name"),
        },
    )


# GET /exercises/new
@login_required
def exercise_new(request):
    return render(
        request,
        "gym_journal/library/form.html",
        _exercise_form_context(from_workout=_from_active_workout(request)),
    )


# POST /exercises/create
def _exercise_form_context(exercise=None, selected_muscles=None, from_workout=False):
    return {
        "exercise": exercise,
        "categories": Exercise.Category.choices,
        "muscles": Muscle.objects.order_by("name"),
        "selected_muscles": selected_muscles or [],
        "from_workout": from_workout,
    }


@login_required
@require_POST
def create_exercise(request):
    new_exercise = Exercise(
        name=request.POST.get('name'),
        category=request.POST.get('category'),
    )
    selected_muscle_ids = request.POST.getlist('targeted_muscles')
    from_workout = _from_active_workout(request)
    try:
        new_exercise.full_clean()
        new_exercise.save()
        muscles = Muscle.objects.filter(id__in=selected_muscle_ids)
        new_exercise.targeted_muscles.set(muscles)
        messages.success(request, "Exercise added.")
        if from_workout:
            return redirect("workout_log_set", exercise_id=new_exercise.pk)
        return redirect("exercise_list")
    except ValidationError as e:
        messages.error(request, _validation_message(e))
        return render(
            request,
            "gym_journal/library/form.html",
            _exercise_form_context(
                exercise=new_exercise,
                selected_muscles=list(Muscle.objects.filter(id__in=selected_muscle_ids)),
                from_workout=from_workout,
            ),
        )


# GET /exercises/:id
@login_required
def exercise_detail(request, exercise_id):
    try:
        exercise = Exercise.objects.prefetch_related("targeted_muscles").get(
            pk=exercise_id
        )
    except Exercise.DoesNotExist:
        return render(request, "gym_journal/library/not_found.html")

    logged_set_count = WorkoutSet.objects.filter(
        exercise=exercise, workout__user=request.user
    ).count()
    global_set_count = WorkoutSet.objects.filter(exercise=exercise).count()
    return render(
        request,
        "gym_journal/library/detail.html",
        {
            "exercise": exercise,
            "logged_set_count": logged_set_count,
            "global_set_count": global_set_count,
            "can_delete_exercise": global_set_count == 0,
        },
    )


# GET /exercises/:id/edit
@login_required
def exercise_edit(request, exercise_id):
    exercise = get_object_or_404(
        Exercise.objects.prefetch_related("targeted_muscles"), pk=exercise_id
    )
    return render(
        request,
        "gym_journal/library/form.html",
        _exercise_form_context(
            exercise=exercise,
            selected_muscles=list(exercise.targeted_muscles.all()),
        ),
    )


# POST /exercises/:id/update
@login_required
@require_POST
def update_exercise(request, exercise_id):
    exercise = get_object_or_404(Exercise, pk=exercise_id)
    exercise.name = request.POST.get('name')
    exercise.category = request.POST.get('category')
    selected_muscle_ids = request.POST.getlist('targeted_muscles')
    try:
        exercise.full_clean()
        exercise.save()
        exercise.targeted_muscles.set(selected_muscle_ids)
        messages.success(request, "Exercise saved.")
        return redirect("exercise_detail", exercise_id=exercise_id)
    except ValidationError as e:
        messages.error(request, _validation_message(e))
        return render(
            request,
            "gym_journal/library/form.html",
            _exercise_form_context(
                exercise=exercise,
                selected_muscles=list(Muscle.objects.filter(id__in=selected_muscle_ids)),
            ),
        )


# POST /exercises/:id/delete
@login_required
@require_POST
def delete_exercise(request, exercise_id):
    exercise = get_object_or_404(Exercise, pk=exercise_id)
    if WorkoutSet.objects.filter(exercise=exercise).exists():
        messages.error(request, "Cannot delete an exercise with logged sets.")
        return redirect("exercise_detail", exercise_id=exercise_id)
    exercise.delete()
    messages.success(request, "Exercise deleted.")
    return redirect("exercise_list")
