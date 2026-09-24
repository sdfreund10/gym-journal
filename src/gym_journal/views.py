import functools
import logging
from datetime import timedelta
from itertools import groupby

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe

from .logging_utils import log_event
from .models import Exercise, Muscle, Workout, WorkoutSet

WEIGHTED_EXERCISE_CATEGORIES = frozenset(
    {
        Exercise.Category.DUMBBELL,
        Exercise.Category.FREE_WEIGHT,
        Exercise.Category.MACHINE,
    }
)


class LoginView(DjangoLoginView):
    template_name = "gym_journal/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        log_event(
            "auth.login.success",
            user_id=self.request.user.pk,
            username=self.request.user.username,
        )
        return response

    def form_invalid(self, form):
        response = super().form_invalid(form)
        username = form.data.get("username", "")
        log_event(
            "auth.login.failed",
            level=logging.WARNING,
            username=username,
        )
        return response


class LogoutView(DjangoLogoutView):
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            log_event(
                "auth.logout",
                user_id=request.user.pk,
                username=request.user.username,
            )
        return super().post(request, *args, **kwargs)


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
    has_weight = category in WEIGHTED_EXERCISE_CATEGORIES
    is_timed = category == Exercise.Category.TIMED
    default_weight = 45 if category == Exercise.Category.FREE_WEIGHT else 25
    return {
        "has_weight": has_weight,
        "is_timed": is_timed,
        "default_weight": default_weight,
        "default_reps": 8,
        "default_duration": 30,
    }


def _set_form_context(
    *,
    workout,
    exercise,
    set_number,
    form_action,
    is_edit=False,
    values=None,
):
    defaults = _category_defaults(exercise.category)
    values = values or {}
    weight_unset = False
    if "weight" in values:
        if values["weight"] in (None, ""):
            weight_unset = True
        else:
            defaults["default_weight"] = values["weight"]
    if "reps" in values:
        defaults["default_reps"] = values["reps"]
    if "duration_seconds" in values:
        defaults["default_duration"] = values["duration_seconds"]
    return {
        "workout": workout,
        "exercise": exercise,
        "next_set_number": set_number,
        "form_action": form_action,
        "is_edit": is_edit,
        "weight_unset": weight_unset,
        **defaults,
    }


WORKOUT_TIMEOUT_LIMIT_MINUTES = 90
INACTIVE_WORKOUT_CHECK_CACHE_SECONDS = 15 * 60


def _inactive_workout_check_cache_key(user_id):
    return f"gym-journal:inactive-workout-check:{user_id}"


def close_inactive_workouts(func):
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return func(request, *args, **kwargs)

        cache_key = _inactive_workout_check_cache_key(request.user.pk)
        if cache.get(cache_key):
            return func(request, *args, **kwargs)

        cutoff = timezone.now() - timedelta(minutes=WORKOUT_TIMEOUT_LIMIT_MINUTES)
        active_workouts = Workout.objects.for_user(request.user).active()
        for workout in active_workouts:
            last_activity_at = workout.last_activity_at()
            if last_activity_at < cutoff:
                workout.finish(ended_at=last_activity_at)
                log_event(
                    "workout.autoclosed",
                    user_id=request.user.pk,
                    username=request.user.username,
                    workout_id=workout.pk,
                )

        cache.set(cache_key, True, timeout=INACTIVE_WORKOUT_CHECK_CACHE_SECONDS)
        return func(request, *args, **kwargs)

    return wrapper


# GET /
@login_required
@close_inactive_workouts
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


def _group_workout_sets(sets):
    exercise_ids = tuple(dict.fromkeys(workout_set.exercise_id for workout_set in sets))
    exercise_order = {
        exercise_id: position for position, exercise_id in enumerate(exercise_ids)
    }
    grouped_sets = groupby(
        sorted(sets, key=lambda workout_set: exercise_order[workout_set.exercise_id]),
        key=lambda workout_set: workout_set.exercise_id,
    )
    return [
        {
            "exercise": exercise_sets[0].exercise,
            "sets": exercise_sets,
            "remaining_count": max(len(exercise_sets) - 3, 0),
        }
        for _, workout_sets in grouped_sets
        if (exercise_sets := list(workout_sets))
    ]


def _workout_detail_context(workout, request):
    sets = list(
        workout.workoutset_set.select_related("exercise").order_by(
            "-logged_at", "-pk"
        )
    )
    if request.GET.get("from") == "history":
        back_url = reverse("workout_history")
        back_label = "History"
    else:
        back_url = reverse("index")
        back_label = "Home"
    return {
        "workout": workout,
        "exercise_groups": _group_workout_sets(sets),
        "set_count": len(sets),
        "is_active": workout.ended_at is None,
        "last_set_logged_at": sets[0].logged_at if sets else None,
        "back_url": back_url,
        "back_label": back_label,
    }


# GET /workout/
@login_required
@close_inactive_workouts
def active_workout_detail(request):
    workout = Workout.objects.for_user(request.user).active().first()
    if not workout:
        return render(request, "gym_journal/workout/no_active.html")

    return redirect("workout_detail", workout_id=workout.id)


# GET /workout/:workout_id/
@login_required
@close_inactive_workouts
def workout_detail(request, workout_id):
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)
    return render(
        request,
        "gym_journal/workout/detail.html",
        _workout_detail_context(workout, request),
    )


# GET /workouts/
@login_required
@close_inactive_workouts
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
@close_inactive_workouts
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
@close_inactive_workouts
def workout_log_set(request, exercise_id):
    workout = Workout.objects.for_user(request.user).active().first()
    if not workout:
        return render(request, "gym_journal/workout/no_active.html")

    exercise = get_object_or_404(Exercise, pk=exercise_id)
    next_set_number = WorkoutSet.next_set_number(workout, exercise)

    return render(
        request,
        "gym_journal/workout/log_set.html",
        {
            **_set_form_context(
                workout=workout,
                exercise=exercise,
                set_number=next_set_number,
                form_action=reverse("log_set", kwargs={"exercise_id": exercise.pk}),
            ),
            "last_weight": exercise.last_weight(request.user),
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
    log_event(
        "workout.started",
        user_id=request.user.pk,
        workout_id=new_workout.pk,
    )
    messages.success(request, "Workout started.")
    return redirect("workout_detail", workout_id=new_workout.id)


# POST /workouts/finish
# Finish latest active workout
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
        log_event(
            "workout.finished",
            user_id=request.user.pk,
            workout_id=active_workout.pk,
        )
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
        log_event(
            "set.logged",
            user_id=request.user.pk,
            workout_id=active_workout.pk,
            set_id=new_set.pk,
            exercise_id=exercise.pk,
        )
        messages.success(request, "Set logged.")
        return redirect("workout_detail", workout_id=active_workout.id)
    except ValidationError as e:
        messages.error(request, _validation_message(e))
        return redirect("workout_log_set", exercise_id=exercise_id)


def _finished_workout_redirect(request, workout):
    messages.error(request, "Cannot modify a finished workout.")
    return redirect("workout_detail", workout_id=workout.id)


def _render_set_edit_form(request, workout_set, values=None):
    if values is None:
        values = {
            "weight": workout_set.weight,
            "reps": workout_set.reps,
            "duration_seconds": workout_set.duration_seconds,
        }
    return render(
        request,
        "gym_journal/workout/log_set.html",
        _set_form_context(
            workout=workout_set.workout,
            exercise=workout_set.exercise,
            set_number=workout_set.set_number,
            form_action=reverse("update_set", kwargs={"set_id": workout_set.pk}),
            is_edit=True,
            values=values,
        ),
    )


def _locked_owned_workout_set(user, set_id):
    """Fetch and lock an owned set and workout inside an atomic transaction."""
    workout_set = get_object_or_404(
        WorkoutSet.objects.select_for_update().select_related("exercise"),
        pk=set_id,
        workout__user=user,
    )
    workout_set.workout = get_object_or_404(
        Workout.objects.select_for_update(),
        pk=workout_set.workout_id,
        user=user,
    )
    return workout_set


def _update_set_measurements(workout_set, post):
    """Validate and save measurements; the caller owns the transaction."""
    has_weight = workout_set.exercise.has_weight()
    is_timed = workout_set.exercise.is_timed()
    workout_set.weight = _optional_post_value(post, "weight") if has_weight else None
    workout_set.reps = None if is_timed else _optional_post_value(post, "reps")
    workout_set.duration_seconds = (
        _optional_post_value(post, "duration_seconds") if is_timed else None
    )
    workout_set.full_clean()
    workout_set.save(update_fields=["weight", "reps", "duration_seconds"])


# GET /workout/set/<set_id>/edit/
@login_required
@close_inactive_workouts
@require_safe
def edit_set(request, set_id):
    workout_set = get_object_or_404(
        WorkoutSet.objects.select_related("workout", "exercise"),
        pk=set_id,
        workout__user=request.user,
    )
    if workout_set.workout.ended_at is not None:
        return _finished_workout_redirect(request, workout_set.workout)

    return _render_set_edit_form(request, workout_set)


# POST /workout/set/<set_id>/update/
@login_required
@require_POST
@transaction.atomic
def update_set(request, set_id):
    workout_set = _locked_owned_workout_set(request.user, set_id)
    if workout_set.workout.ended_at is not None:
        return _finished_workout_redirect(request, workout_set.workout)

    try:
        _update_set_measurements(workout_set, request.POST)
    except ValidationError as e:
        messages.error(request, _validation_message(e))
        return _render_set_edit_form(
            request,
            workout_set,
            values={
                "weight": request.POST.get("weight"),
                "reps": request.POST.get("reps"),
                "duration_seconds": request.POST.get("duration_seconds"),
            },
        )

    log_event(
        "set.updated",
        user_id=request.user.pk,
        workout_id=workout_set.workout_id,
        set_id=workout_set.pk,
        exercise_id=workout_set.exercise_id,
    )
    messages.success(request, "Set updated.")
    return redirect("workout_detail", workout_id=workout_set.workout_id)


# POST /workout/set/<set_id>/delete/
@login_required
@require_POST
def delete_set(request, set_id):
    workout_set = get_object_or_404(WorkoutSet, pk=set_id, workout__user=request.user)
    workout = workout_set.workout
    if workout.ended_at is not None:
        return _finished_workout_redirect(request, workout)

    log_event(
        "set.deleted",
        user_id=request.user.pk,
        workout_id=workout_set.workout_id,
        set_id=workout_set.pk,
        exercise_id=workout_set.exercise_id,
    )
    workout_set.delete()
    messages.success(request, "Set removed.")
    return redirect("workout_detail", workout_id=workout.id)


# GET /exercises
@login_required
@close_inactive_workouts
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
@close_inactive_workouts
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
        name=request.POST.get("name"),
        category=request.POST.get("category"),
    )
    selected_muscle_ids = request.POST.getlist("targeted_muscles")
    from_workout = _from_active_workout(request)
    try:
        new_exercise.full_clean()
        new_exercise.save()
        muscles = Muscle.objects.filter(id__in=selected_muscle_ids)
        new_exercise.targeted_muscles.set(muscles)
        log_event(
            "exercise.created",
            user_id=request.user.pk,
            exercise_id=new_exercise.pk,
        )
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
                selected_muscles=list(
                    Muscle.objects.filter(id__in=selected_muscle_ids)
                ),
                from_workout=from_workout,
            ),
        )


# GET /exercises/:id
@login_required
@close_inactive_workouts
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
@close_inactive_workouts
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
    exercise.name = request.POST.get("name")
    exercise.category = request.POST.get("category")
    selected_muscle_ids = request.POST.getlist("targeted_muscles")
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
                selected_muscles=list(
                    Muscle.objects.filter(id__in=selected_muscle_ids)
                ),
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

    log_event(
        "exercise.deleted",
        user_id=request.user.pk,
        exercise_id=exercise.pk,
    )
    exercise.delete()
    messages.success(request, "Exercise deleted.")
    return redirect("exercise_list")
