from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from .models import Task


class MarkTaskDoneTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.other_user = User.objects.create_user(
            username="bob", password="testpass123"
        )

    def test_mark_task_done_sets_completion_flag(self):
        task = Task.objects.create(title="Write tests", user=self.user)
        self.client.login(username="alice", password="testpass123")

        response = self.client.post(reverse("mark_task_done", args=[task.id]))

        self.assertRedirects(response, reverse("task_list"))
        task.refresh_from_db()
        self.assertTrue(task.is_completed)

    def test_mark_task_done_cannot_modify_other_users_task(self):
        task = Task.objects.create(title="Private task", user=self.other_user)
        self.client.login(username="alice", password="testpass123")

        response = self.client.post(reverse("mark_task_done", args=[task.id]))

        self.assertEqual(response.status_code, 404)
        task.refresh_from_db()
        self.assertFalse(task.is_completed)

    def test_mark_task_done_rejects_get(self):
        task = Task.objects.create(title="Needs POST", user=self.user)
        self.client.login(username="alice", password="testpass123")

        response = self.client.get(reverse("mark_task_done", args=[task.id]))

        self.assertEqual(response.status_code, 405)


class TaskCreationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")

    def test_create_task_via_post(self):
        self.client.login(username="alice", password="testpass123")
        response = self.client.post(
            reverse("create_task"),
            {"title": "New task", "description": "Test description", "priority": 0},
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(Task.objects.filter(title="New task", user=self.user).exists())

    def test_create_task_requires_login(self):
        response = self.client.post(
            reverse("create_task"),
            {"title": "Sneaky task"},
        )
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('create_task')}")
