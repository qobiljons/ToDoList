from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("tasks/", views.task_list, name="task_list"),
    path("analysis/", views.analysis, name="analysis"),
    path("register/", views.register, name="register"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("create/", views.create_task, name="create_task"),
    path("edit/<int:task_id>/", views.edit_task, name="edit_task"),
    path("delete/<int:task_id>/", views.delete_task, name="delete_task"),
    path("categories/", views.categories, name="categories"),
    path(
        "subtask/<int:subtask_id>/toggle/", views.toggle_subtask, name="toggle_subtask"
    ),
]
