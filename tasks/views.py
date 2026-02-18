from django.shortcuts import render

from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.shortcuts import render, redirect, get_object_or_404
from .models import Task, Category, SubTask, Tag
from django.http import HttpResponseRedirect


# Home / Dashboard
@login_required
def dashboard(request):
    tasks = Task.objects.filter(user=request.user)

    total_tasks = tasks.count()
    completed_tasks = tasks.filter(is_completed=True).count()
    pending_tasks = total_tasks - completed_tasks
    completion_rate = (
        round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0
    )

    recent_tasks = tasks.order_by("-created_at")[:5]
    urgent_tasks = tasks.filter(priority__gte=2, is_completed=False).order_by(
        "due_date"
    )[:5]

    return render(
        request,
        "tasks/dashboard.html",
        {
            "tasks": tasks,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "completion_rate": completion_rate,
            "recent_tasks": recent_tasks,
            "urgent_tasks": urgent_tasks,
        },
    )


# Task List
@login_required
def task_list(request):
    tasks = Task.objects.filter(user=request.user)
    return render(request, "tasks/task_list.html", {"tasks": tasks})


# Analysis
@login_required
def analysis(request):
    tasks = Task.objects.filter(user=request.user)

    total_tasks = tasks.count()
    completed_tasks = tasks.filter(is_completed=True).count()
    pending_tasks = total_tasks - completed_tasks

    by_priority = {
        "urgent": tasks.filter(priority=3).count(),
        "high": tasks.filter(priority=2).count(),
        "medium": tasks.filter(priority=1).count(),
        "low": tasks.filter(priority=0).count(),
    }

    by_category = {}
    for cat in Category.objects.filter(user=request.user):
        by_category[cat.name] = tasks.filter(category=cat).count()

    by_tag = {}
    for tag in Tag.objects.filter(user=request.user):
        by_tag[tag.name] = tag.tasks.filter(user=request.user).count()

    overdue_tasks = tasks.filter(due_date__lt="2026-02-18", is_completed=False).count()

    upcoming_tasks = tasks.filter(
        due_date__gte="2026-02-18", due_date__lte="2026-02-25", is_completed=False
    ).count()

    completion_rate = (
        round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0
    )

    return render(
        request,
        "tasks/analysis.html",
        {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "by_priority": by_priority,
            "by_category": by_category,
            "by_tag": by_tag,
            "overdue_tasks": overdue_tasks,
            "upcoming_tasks": upcoming_tasks,
            "completion_rate": completion_rate,
        },
    )


# Register


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = UserCreationForm()
    return render(request, "tasks/register.html", {"form": form})


# Login


def user_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("dashboard")
    else:
        form = AuthenticationForm()
    return render(request, "tasks/login.html", {"form": form})


# Logout
def user_logout(request):
    logout(request)
    return redirect("login")


# Task List (Dashboard is reused)


# Create Task
@login_required
def create_task(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        category_id = request.POST.get("category")
        priority = request.POST.get("priority", 0)
        due_date = request.POST.get("due_date")
        category = Category.objects.get(id=category_id) if category_id else None
        task = Task.objects.create(
            title=title,
            description=description,
            user=request.user,
            category=category,
            priority=priority,
            due_date=due_date,
        )
        tag_ids = request.POST.getlist("tags")
        if tag_ids:
            tags = Tag.objects.filter(id__in=tag_ids, user=request.user)
            task.tags.set(tags)
        return redirect("dashboard")
    categories = Category.objects.filter(user=request.user)
    tags = Tag.objects.filter(user=request.user)
    return render(
        request, "tasks/create_task.html", {"categories": categories, "tags": tags}
    )


# Edit Task
@login_required
def edit_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    if request.method == "POST":
        if "add_subtask" in request.POST:
            subtask_title = request.POST.get("subtask_title")
            if subtask_title:
                SubTask.objects.create(title=subtask_title, task=task)
            return redirect("edit_task", task_id=task.id)

        task.title = request.POST.get("title")
        task.description = request.POST.get("description")
        category_id = request.POST.get("category")
        task.priority = request.POST.get("priority", 0)
        due_date = request.POST.get("due_date")
        task.due_date = due_date if due_date else None
        task.is_completed = request.POST.get("is_completed") == "on"
        task.category = Category.objects.get(id=category_id) if category_id else None
        task.save()

        tag_ids = request.POST.getlist("tags")
        tags = Tag.objects.filter(id__in=tag_ids, user=request.user)
        task.tags.set(tags)

        return redirect("dashboard")
    categories = Category.objects.filter(user=request.user)
    subtasks = SubTask.objects.filter(task=task)
    user_tags = Tag.objects.filter(user=request.user)
    return render(
        request,
        "tasks/edit_task.html",
        {
            "task": task,
            "categories": categories,
            "subtasks": subtasks,
            "tags": user_tags,
        },
    )


# Delete Task
@login_required
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    if request.method == "POST":
        task.delete()
        return redirect("dashboard")
    return render(request, "tasks/delete_task.html", {"task": task})


# Categories page
@login_required
def categories(request):
    if request.method == "POST":
        if "tag_name" in request.POST:
            tag_name = request.POST.get("tag_name")
            if tag_name:
                Tag.objects.create(name=tag_name, user=request.user)
        else:
            name = request.POST.get("name")
            if name:
                Category.objects.create(name=name, user=request.user)
        return redirect("categories")
    user_categories = Category.objects.filter(user=request.user)
    user_tags = Tag.objects.filter(user=request.user)
    return render(
        request,
        "tasks/categories.html",
        {"categories": user_categories, "tags": user_tags},
    )


# Toggle SubTask
@login_required
def toggle_subtask(request, subtask_id):
    subtask = get_object_or_404(SubTask, task__user=request.user, id=subtask_id)
    subtask.is_completed = not subtask.is_completed
    subtask.save()
    return redirect("edit_task", task_id=subtask.task.id)
