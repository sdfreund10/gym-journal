from django.urls import path

from . import views

urlpatterns = [
    path("auth/login/", views.LoginView.as_view(), name="api_login"),
    path("auth/logout/", views.LogoutView.as_view(), name="api_logout"),
    path("auth/me/", views.MeView.as_view(), name="api_me"),
    path("summary/", views.SummaryView.as_view(), name="api_summary"),
    path("workouts/", views.WorkoutListView.as_view(), name="api_workout_list"),
    path(
        "workouts/active/",
        views.ActiveWorkoutView.as_view(),
        name="api_active_workout",
    ),
    path(
        "workouts/start/",
        views.StartWorkoutView.as_view(),
        name="api_start_workout",
    ),
    path(
        "workouts/finish/",
        views.FinishWorkoutView.as_view(),
        name="api_finish_workout",
    ),
    path(
        "workouts/active/sets/",
        views.LogSetView.as_view(),
        name="api_log_set",
    ),
    path(
        "workouts/<int:workout_id>/",
        views.WorkoutDetailView.as_view(),
        name="api_workout_detail",
    ),
    path(
        "sets/<int:set_id>/",
        views.DeleteSetView.as_view(),
        name="api_delete_set",
    ),
    path("muscles/", views.MuscleListView.as_view(), name="api_muscle_list"),
    path("exercises/", views.ExerciseListCreateView.as_view(), name="api_exercise_list"),
    path(
        "exercises/<int:exercise_id>/",
        views.ExerciseDetailView.as_view(),
        name="api_exercise_detail",
    ),
]
