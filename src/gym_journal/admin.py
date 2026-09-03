from django.contrib import admin

from .models import Muscle, Workout, WorkoutSet, Exercise

# Create superuser from command line
# python manage.py createsuperuser

admin.site.register(Muscle)
admin.site.register(Exercise)
admin.site.register(WorkoutSet)


@admin.register(Workout)
class WorkoutAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "started_at", "ended_at")
    list_filter = ("ended_at",)
    raw_id_fields = ("user",)
