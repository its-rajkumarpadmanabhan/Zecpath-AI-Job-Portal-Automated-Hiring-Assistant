from django.contrib import admin
from .models import User, Job, Application


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("name", "email")


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "company", "posted_by", "created_at")
    list_filter = ("company",)
    search_fields = ("title", "company")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "candidate", "job", "status", "applied_at")
    list_filter = ("status",)
    search_fields = ("candidate__name", "job__title")