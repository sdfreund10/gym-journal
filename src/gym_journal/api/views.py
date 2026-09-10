from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from gym_journal.models import Exercise, Muscle, Workout, WorkoutSet

from .serializers import (
    ExerciseSerializer,
    LoginSerializer,
    MuscleSerializer,
    SummarySerializer,
    UserSerializer,
    WorkoutDetailSerializer,
    WorkoutListSerializer,
    WorkoutSetSerializer,
)


def _django_validation_to_drf(exc):
    if hasattr(exc, "message_dict"):
        return ValidationError(exc.message_dict)
    return ValidationError(list(exc.messages) if exc.messages else [str(exc)])


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _created = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user": UserSerializer(user).data,
            }
        )


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class SummaryView(APIView):
    def get(self, request):
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
            last_workout.set_count = last_workout_set_count

        payload = {
            "active_workout_id": active_workout.id if active_workout else None,
            "exercise_count": Exercise.objects.count(),
            "finished_workout_count": user_workouts.filter(
                ended_at__isnull=False
            ).count(),
            "active_set_count": active_set_count,
            "today_set_count": active_set_count,
            "last_workout": last_workout,
            "last_workout_set_count": last_workout_set_count,
        }
        return Response(SummarySerializer(payload).data)


class WorkoutListView(generics.ListAPIView):
    serializer_class = WorkoutListSerializer

    def get_queryset(self):
        return (
            Workout.objects.for_user(self.request.user)
            .annotate(set_count=Count("workoutset"))
            .order_by("-started_at")
        )


class ActiveWorkoutView(APIView):
    def get(self, request):
        workout = Workout.objects.for_user(request.user).active().first()
        if not workout:
            raise NotFound("No active workout.")
        return Response(WorkoutDetailSerializer(workout).data)


class WorkoutDetailView(generics.RetrieveAPIView):
    serializer_class = WorkoutDetailSerializer
    lookup_url_kwarg = "workout_id"

    def get_queryset(self):
        return Workout.objects.for_user(self.request.user)


class StartWorkoutView(APIView):
    def post(self, request):
        try:
            workout = Workout.start(request.user)
        except DjangoValidationError as exc:
            raise _django_validation_to_drf(exc) from exc
        return Response(
            WorkoutDetailSerializer(workout).data,
            status=status.HTTP_201_CREATED,
        )


class FinishWorkoutView(APIView):
    def post(self, request):
        workout = Workout.objects.for_user(request.user).active().first()
        if not workout:
            raise NotFound("No active workout to finish.")
        workout.finish()
        return Response(WorkoutDetailSerializer(workout).data)


class LogSetView(APIView):
    def post(self, request):
        workout = Workout.objects.for_user(request.user).active().first()
        if not workout:
            raise NotFound("No active workout.")

        serializer = WorkoutSetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        exercise = serializer.validated_data["exercise"]
        new_set = WorkoutSet(
            workout=workout,
            exercise=exercise,
            logged_at=timezone.now(),
            weight=serializer.validated_data.get("weight"),
            reps=serializer.validated_data.get("reps"),
            duration_seconds=serializer.validated_data.get("duration_seconds"),
        )
        try:
            new_set.full_clean()
            new_set.save()
        except DjangoValidationError as exc:
            raise _django_validation_to_drf(exc) from exc

        return Response(
            WorkoutSetSerializer(new_set).data,
            status=status.HTTP_201_CREATED,
        )


class DeleteSetView(APIView):
    def delete(self, request, set_id):
        workout_set = (
            WorkoutSet.objects.filter(pk=set_id, workout__user=request.user)
            .select_related("workout", "exercise")
            .first()
        )
        if workout_set is None:
            raise NotFound()
        if workout_set.workout.ended_at is not None:
            raise PermissionDenied("Cannot modify a finished workout.")
        workout_set.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MuscleListView(generics.ListAPIView):
    serializer_class = MuscleSerializer
    queryset = Muscle.objects.order_by("name")
    pagination_class = None


class ExerciseListCreateView(generics.ListCreateAPIView):
    serializer_class = ExerciseSerializer

    def get_queryset(self):
        qs = Exercise.objects.prefetch_related("targeted_muscles").order_by("name")
        if self.request.query_params.get("ordered") == "recency":
            # Preserve model helper order (recent first, then name).
            ordered = Exercise.ordered_by_recency(self.request.user)
            id_order = {ex.pk: index for index, ex in enumerate(ordered)}
            return sorted(qs, key=lambda ex: id_order.get(ex.pk, 999))
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if isinstance(queryset, list):
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        return super().list(request, *args, **kwargs)


class ExerciseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExerciseSerializer
    lookup_url_kwarg = "exercise_id"
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Exercise.objects.prefetch_related("targeted_muscles")

    def perform_destroy(self, instance):
        if WorkoutSet.objects.filter(exercise=instance).exists():
            raise ValidationError("Cannot delete an exercise with logged sets.")
        instance.delete()
