from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("", views.index, name="index"),
    path("workout/", views.active_workout_detail, name="active_workout_detail"),
    path("workout/add/", views.workout_pick_exercise, name="workout_pick_exercise"),
    path(
        "workout/add/<int:exercise_id>/",
        views.workout_log_set,
        name="workout_log_set",
    ),
    path("workouts/", views.workout_history, name="workout_history"),
    path("workouts/start/", views.start_workout, name="start_workout"),
    path("workouts/finish/", views.finish_workout, name="finish_workout"),
    path("workout/<int:workout_id>/", views.workout_detail, name="workout_detail"),
    path("workout/log/<int:exercise_id>/", views.log_set, name="log_set"),
    path("workout/set/<int:set_id>/delete/", views.delete_set, name="delete_set"),
    path("exercises/", views.exercise_list, name="exercise_list"),
    path("exercises/new/", views.exercise_new, name="exercise_new"),
    path("exercises/create/", views.create_exercise, name="exercise_create"),
    path("exercises/<int:exercise_id>/", views.exercise_detail, name="exercise_detail"),
    path(
        "exercises/<int:exercise_id>/edit/", views.exercise_edit, name="exercise_edit"
    ),
    path(
        "exercises/<int:exercise_id>/update/",
        views.update_exercise,
        name="exercise_update",
    ),
    path(
        "exercises/<int:exercise_id>/delete/",
        views.delete_exercise,
        name="exercise_delete",
    ),
]
