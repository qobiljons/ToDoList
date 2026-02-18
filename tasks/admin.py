from django.contrib import admin
from .models import Category, Task, SubTask


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "created_at")
    list_filter = ("user",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "category",
        "priority",
        "is_completed",
        "due_date",
        "created_at",
    )
    list_filter = ("is_completed", "priority", "category", "user")
    search_fields = ("title", "description")


@admin.register(SubTask)
class SubTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "task", "is_completed")
    list_filter = ("is_completed",)
