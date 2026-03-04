from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from .models import Task, Category, Tag, SubTask


class CategoryModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")

    def test_create_category(self):
        cat = Category.objects.create(name="Work", user=self.user)
        self.assertEqual(cat.name, "Work")
        self.assertEqual(cat.user, self.user)
        self.assertIsNotNone(cat.created_at)

    def test_category_cascade_delete_with_user(self):
        Category.objects.create(name="Work", user=self.user)
        self.user.delete()
        self.assertEqual(Category.objects.count(), 0)


class TaskModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")

    def test_create_task_defaults(self):
        task = Task.objects.create(title="My task", user=self.user)
        self.assertEqual(task.priority, 0)
        self.assertFalse(task.is_completed)
        self.assertIsNone(task.due_date)
        self.assertIsNone(task.category)
        self.assertEqual(task.description, "")

    def test_task_with_category(self):
        cat = Category.objects.create(name="Work", user=self.user)
        task = Task.objects.create(title="Task", user=self.user, category=cat)
        self.assertEqual(task.category, cat)

    def test_category_set_null_on_delete(self):
        cat = Category.objects.create(name="Work", user=self.user)
        task = Task.objects.create(title="Task", user=self.user, category=cat)
        cat.delete()
        task.refresh_from_db()
        self.assertIsNone(task.category)

    def test_task_cascade_delete_with_user(self):
        Task.objects.create(title="Task", user=self.user)
        self.user.delete()
        self.assertEqual(Task.objects.count(), 0)


class TagModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")

    def test_create_tag(self):
        tag = Tag.objects.create(name="urgent", user=self.user)
        self.assertEqual(str(tag), "urgent")

    def test_tag_task_relationship(self):
        tag = Tag.objects.create(name="urgent", user=self.user)
        task = Task.objects.create(title="Task", user=self.user)
        tag.tasks.add(task)
        self.assertIn(tag, task.tags.all())
        self.assertIn(task, tag.tasks.all())


class SubTaskModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.task = Task.objects.create(title="Parent", user=self.user)

    def test_create_subtask(self):
        sub = SubTask.objects.create(title="Child", task=self.task)
        self.assertFalse(sub.is_completed)
        self.assertEqual(sub.task, self.task)

    def test_subtask_cascade_delete_with_task(self):
        SubTask.objects.create(title="Child", task=self.task)
        self.task.delete()
        self.assertEqual(SubTask.objects.count(), 0)


class RegistrationTests(TestCase):
    def test_register_page_loads(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)

    def test_register_creates_user_and_redirects(self):
        response = self.client.post(reverse("register"), {
            "username": "newuser",
            "password1": "complexpass123!",
            "password2": "complexpass123!",
        })
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_invalid_password_mismatch(self):
        response = self.client.post(reverse("register"), {
            "username": "newuser",
            "password1": "complexpass123!",
            "password2": "wrongpass",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")

    def test_login_page_loads(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_login_valid_credentials(self):
        response = self.client.post(reverse("login"), {
            "username": "alice",
            "password": "testpass123",
        })
        self.assertRedirects(response, reverse("dashboard"))

    def test_login_invalid_credentials(self):
        response = self.client.post(reverse("login"), {
            "username": "alice",
            "password": "wrong",
        })
        self.assertEqual(response.status_code, 200)

    def test_logout_redirects_to_login(self):
        self.client.login(username="alice", password="testpass123")
        response = self.client.get(reverse("logout"))
        self.assertRedirects(response, reverse("login"))


class DashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.client.login(username="alice", password="testpass123")

    def test_dashboard_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_dashboard_loads(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_context_empty(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["total_tasks"], 0)
        self.assertEqual(response.context["completed_tasks"], 0)
        self.assertEqual(response.context["pending_tasks"], 0)
        self.assertEqual(response.context["completion_rate"], 0)

    def test_dashboard_context_with_tasks(self):
        Task.objects.create(title="T1", user=self.user, is_completed=True)
        Task.objects.create(title="T2", user=self.user, is_completed=False)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["total_tasks"], 2)
        self.assertEqual(response.context["completed_tasks"], 1)
        self.assertEqual(response.context["pending_tasks"], 1)
        self.assertEqual(response.context["completion_rate"], 50.0)

    def test_dashboard_shows_only_own_tasks(self):
        other = User.objects.create_user(username="bob", password="testpass123")
        Task.objects.create(title="Alice task", user=self.user)
        Task.objects.create(title="Bob task", user=other)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["total_tasks"], 1)

    def test_dashboard_urgent_tasks(self):
        Task.objects.create(title="Urgent", user=self.user, priority=3)
        Task.objects.create(title="Low", user=self.user, priority=0)
        response = self.client.get(reverse("dashboard"))
        urgent = list(response.context["urgent_tasks"])
        self.assertEqual(len(urgent), 1)
        self.assertEqual(urgent[0].title, "Urgent")


class TaskListViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.client.login(username="alice", password="testpass123")

    def test_task_list_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("task_list"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('task_list')}")

    def test_task_list_loads(self):
        response = self.client.get(reverse("task_list"))
        self.assertEqual(response.status_code, 200)

    def test_task_list_shows_only_own_tasks(self):
        other = User.objects.create_user(username="bob", password="testpass123")
        Task.objects.create(title="Mine", user=self.user)
        Task.objects.create(title="Theirs", user=other)
        response = self.client.get(reverse("task_list"))
        tasks = list(response.context["tasks"])
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].title, "Mine")


class TaskCreationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")

    def test_create_task_page_loads(self):
        self.client.login(username="alice", password="testpass123")
        response = self.client.get(reverse("create_task"))
        self.assertEqual(response.status_code, 200)

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
        self.assertRedirects(
            response, f"{reverse('login')}?next={reverse('create_task')}"
        )

    def test_create_task_with_category(self):
        self.client.login(username="alice", password="testpass123")
        cat = Category.objects.create(name="Work", user=self.user)
        self.client.post(reverse("create_task"), {
            "title": "Categorized",
            "description": "",
            "priority": 1,
            "category": cat.id,
        })
        task = Task.objects.get(title="Categorized")
        self.assertEqual(task.category, cat)

    def test_create_task_with_tags(self):
        self.client.login(username="alice", password="testpass123")
        tag1 = Tag.objects.create(name="urgent", user=self.user)
        tag2 = Tag.objects.create(name="work", user=self.user)
        self.client.post(reverse("create_task"), {
            "title": "Tagged",
            "description": "",
            "priority": 0,
            "tags": [tag1.id, tag2.id],
        })
        task = Task.objects.get(title="Tagged")
        self.assertEqual(task.tags.count(), 2)

    def test_create_task_with_due_date(self):
        self.client.login(username="alice", password="testpass123")
        self.client.post(reverse("create_task"), {
            "title": "Deadline",
            "description": "",
            "priority": 2,
            "due_date": "2026-12-31",
        })
        task = Task.objects.get(title="Deadline")
        self.assertEqual(str(task.due_date), "2026-12-31")


class EditTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.other_user = User.objects.create_user(
            username="bob", password="testpass123"
        )
        self.client.login(username="alice", password="testpass123")
        self.task = Task.objects.create(
            title="Original", description="Desc", user=self.user, priority=0
        )

    def test_edit_task_page_loads(self):
        response = self.client.get(reverse("edit_task", args=[self.task.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["task"], self.task)

    def test_edit_task_updates_fields(self):
        self.client.post(reverse("edit_task", args=[self.task.id]), {
            "title": "Updated",
            "description": "New desc",
            "priority": 2,
        })
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Updated")
        self.assertEqual(self.task.description, "New desc")
        self.assertEqual(self.task.priority, 2)

    def test_edit_task_mark_completed(self):
        self.client.post(reverse("edit_task", args=[self.task.id]), {
            "title": "Done",
            "description": "",
            "priority": 0,
            "is_completed": "on",
        })
        self.task.refresh_from_db()
        self.assertTrue(self.task.is_completed)

    def test_edit_task_cannot_access_other_users_task(self):
        other_task = Task.objects.create(title="Bob's", user=self.other_user)
        response = self.client.get(reverse("edit_task", args=[other_task.id]))
        self.assertEqual(response.status_code, 404)

    def test_edit_task_add_subtask(self):
        self.client.post(reverse("edit_task", args=[self.task.id]), {
            "add_subtask": "1",
            "subtask_title": "Sub item",
        })
        self.assertEqual(SubTask.objects.filter(task=self.task).count(), 1)
        self.assertEqual(SubTask.objects.first().title, "Sub item")

    def test_edit_task_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("edit_task", args=[self.task.id]))
        self.assertEqual(response.status_code, 302)


class DeleteTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.other_user = User.objects.create_user(
            username="bob", password="testpass123"
        )
        self.client.login(username="alice", password="testpass123")
        self.task = Task.objects.create(title="To delete", user=self.user)

    def test_delete_task_confirmation_page(self):
        response = self.client.get(reverse("delete_task", args=[self.task.id]))
        self.assertEqual(response.status_code, 200)

    def test_delete_task_via_post(self):
        response = self.client.post(reverse("delete_task", args=[self.task.id]))
        self.assertRedirects(response, reverse("dashboard"))
        self.assertFalse(Task.objects.filter(id=self.task.id).exists())

    def test_delete_task_cannot_delete_other_users_task(self):
        other_task = Task.objects.create(title="Bob's", user=self.other_user)
        response = self.client.post(reverse("delete_task", args=[other_task.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Task.objects.filter(id=other_task.id).exists())


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


class CategoriesViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.client.login(username="alice", password="testpass123")

    def test_categories_page_loads(self):
        response = self.client.get(reverse("categories"))
        self.assertEqual(response.status_code, 200)

    def test_create_category(self):
        self.client.post(reverse("categories"), {"name": "Work"})
        self.assertTrue(Category.objects.filter(name="Work", user=self.user).exists())

    def test_create_tag_via_categories(self):
        self.client.post(reverse("categories"), {"tag_name": "urgent"})
        self.assertTrue(Tag.objects.filter(name="urgent", user=self.user).exists())

    def test_categories_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("categories"))
        self.assertEqual(response.status_code, 302)

    def test_categories_shows_only_own_data(self):
        other = User.objects.create_user(username="bob", password="testpass123")
        Category.objects.create(name="Alice cat", user=self.user)
        Category.objects.create(name="Bob cat", user=other)
        response = self.client.get(reverse("categories"))
        cats = list(response.context["categories"])
        self.assertEqual(len(cats), 1)
        self.assertEqual(cats[0].name, "Alice cat")


class ToggleSubtaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.other_user = User.objects.create_user(
            username="bob", password="testpass123"
        )
        self.client.login(username="alice", password="testpass123")
        self.task = Task.objects.create(title="Parent", user=self.user)
        self.subtask = SubTask.objects.create(title="Child", task=self.task)

    def test_toggle_subtask_completes(self):
        response = self.client.get(reverse("toggle_subtask", args=[self.subtask.id]))
        self.subtask.refresh_from_db()
        self.assertTrue(self.subtask.is_completed)
        self.assertRedirects(response, reverse("edit_task", args=[self.task.id]))

    def test_toggle_subtask_uncompletes(self):
        self.subtask.is_completed = True
        self.subtask.save()
        self.client.get(reverse("toggle_subtask", args=[self.subtask.id]))
        self.subtask.refresh_from_db()
        self.assertFalse(self.subtask.is_completed)

    def test_toggle_subtask_cannot_access_other_users(self):
        other_task = Task.objects.create(title="Bob's", user=self.other_user)
        other_sub = SubTask.objects.create(title="Bob's sub", task=other_task)
        response = self.client.get(reverse("toggle_subtask", args=[other_sub.id]))
        self.assertEqual(response.status_code, 404)


class AnalysisViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.client.login(username="alice", password="testpass123")

    def test_analysis_page_loads(self):
        response = self.client.get(reverse("analysis"))
        self.assertEqual(response.status_code, 200)

    def test_analysis_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("analysis"))
        self.assertEqual(response.status_code, 302)

    def test_analysis_context_empty(self):
        response = self.client.get(reverse("analysis"))
        self.assertEqual(response.context["total_tasks"], 0)
        self.assertEqual(response.context["completion_rate"], 0)

    def test_analysis_priority_breakdown(self):
        Task.objects.create(title="T1", user=self.user, priority=0)
        Task.objects.create(title="T2", user=self.user, priority=1)
        Task.objects.create(title="T3", user=self.user, priority=2)
        Task.objects.create(title="T4", user=self.user, priority=3)
        response = self.client.get(reverse("analysis"))
        by_priority = response.context["by_priority"]
        self.assertEqual(by_priority["low"], 1)
        self.assertEqual(by_priority["medium"], 1)
        self.assertEqual(by_priority["high"], 1)
        self.assertEqual(by_priority["urgent"], 1)

    def test_analysis_category_breakdown(self):
        cat = Category.objects.create(name="Work", user=self.user)
        Task.objects.create(title="T1", user=self.user, category=cat)
        Task.objects.create(title="T2", user=self.user, category=cat)
        response = self.client.get(reverse("analysis"))
        self.assertEqual(response.context["by_category"]["Work"], 2)

    def test_analysis_shows_only_own_data(self):
        other = User.objects.create_user(username="bob", password="testpass123")
        Task.objects.create(title="Mine", user=self.user)
        Task.objects.create(title="Theirs", user=other)
        response = self.client.get(reverse("analysis"))
        self.assertEqual(response.context["total_tasks"], 1)
