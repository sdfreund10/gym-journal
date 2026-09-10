from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from gym_journal.models import Exercise, Muscle, Workout, WorkoutSet

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username")


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs["username"],
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError("Invalid username or password.")
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")
        attrs["user"] = user
        return attrs


class MuscleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Muscle
        fields = ("id", "name")


class ExerciseSerializer(serializers.ModelSerializer):
    targeted_muscles = MuscleSerializer(many=True, read_only=True)
    targeted_muscle_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Muscle.objects.all(),
        source="targeted_muscles",
        write_only=True,
        required=False,
    )
    last_weight = serializers.SerializerMethodField()

    class Meta:
        model = Exercise
        fields = (
            "id",
            "name",
            "category",
            "targeted_muscles",
            "targeted_muscle_ids",
            "last_weight",
        )

    def get_last_weight(self, exercise):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return None
        weight = exercise.last_weight(request.user)
        return str(weight) if weight is not None else None

    def create(self, validated_data):
        muscles = validated_data.pop("targeted_muscles", [])
        exercise = Exercise(**validated_data)
        try:
            exercise.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            ) from exc
        exercise.save()
        if muscles:
            exercise.targeted_muscles.set(muscles)
        return exercise

    def update(self, instance, validated_data):
        muscles = validated_data.pop("targeted_muscles", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            ) from exc
        instance.save()
        if muscles is not None:
            instance.targeted_muscles.set(muscles)
        return instance


class WorkoutSetSerializer(serializers.ModelSerializer):
    exercise = serializers.PrimaryKeyRelatedField(queryset=Exercise.objects.all())
    exercise_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = WorkoutSet
        fields = (
            "id",
            "exercise",
            "exercise_detail",
            "logged_at",
            "weight",
            "reps",
            "duration_seconds",
            "set_number",
        )
        read_only_fields = ("id", "logged_at", "set_number", "exercise_detail")

    def get_exercise_detail(self, workout_set):
        exercise = workout_set.exercise
        return {
            "id": exercise.id,
            "name": exercise.name,
            "category": exercise.category,
        }


class WorkoutListSerializer(serializers.ModelSerializer):
    set_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Workout
        fields = ("id", "started_at", "ended_at", "set_count")


class WorkoutDetailSerializer(serializers.ModelSerializer):
    sets = serializers.SerializerMethodField()
    set_count = serializers.SerializerMethodField()

    class Meta:
        model = Workout
        fields = ("id", "started_at", "ended_at", "set_count", "sets")

    def get_sets(self, workout):
        sets = workout.workoutset_set.select_related("exercise").order_by("-logged_at")
        return WorkoutSetSerializer(sets, many=True).data

    def get_set_count(self, workout):
        return workout.workoutset_set.count()


class SummarySerializer(serializers.Serializer):
    active_workout_id = serializers.IntegerField(allow_null=True)
    exercise_count = serializers.IntegerField()
    finished_workout_count = serializers.IntegerField()
    active_set_count = serializers.IntegerField()
    today_set_count = serializers.IntegerField(
        help_text="Deprecated. Use active_set_count."
    )
    last_workout = WorkoutListSerializer(allow_null=True)
    last_workout_set_count = serializers.IntegerField()
