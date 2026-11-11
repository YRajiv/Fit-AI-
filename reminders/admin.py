from django.contrib import admin
from .models import Reminder


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'reminder_type',
        'title',
        'reminder_date',
        'reminder_time',
        'repeat',
        'is_completed',
        'is_active'
    )


    list_filter = (
        'reminder_type',
        'repeat',
        'is_completed',
        'is_active',
        'reminder_date'
    )


    search_fields = (
        'user__username',
        'title'
    )


    readonly_fields = (
        'created_at',
    )


    fieldsets = (

        ("User Information", {
            "fields": (
                "user",
            )
        }),


        ("Reminder Details", {
            "fields": (
                "reminder_type",
                "title",
                "description"
            )
        }),


        ("Schedule", {
            "fields": (
                "reminder_date",
                "reminder_time",
                "repeat"
            )
        }),


        ("Status", {
            "fields": (
                "is_completed",
                "is_active",
                "notification_sent"
            )
        }),


        ("Created Information", {
            "fields": (
                "created_at",
            )
        }),
    )

# Register your models here.
