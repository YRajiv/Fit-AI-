import json
from datetime import timedelta

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from .models import DailyProgress


# ============================================================
# MODEL TESTS
# ============================================================

class DailyProgressModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="progress_user",
            password="testpass123"
        )

    def test_create_daily_progress(self):
        progress = DailyProgress.objects.create(
            user=self.user,
            date=timezone.localdate()
        )

        self.assertEqual(progress.user, self.user)
        self.assertEqual(progress.steps, 0)
        self.assertEqual(progress.steps_goal, 8000)

    def test_default_values(self):
        progress = DailyProgress.objects.create(
            user=self.user,
            date=timezone.localdate()
        )

        self.assertEqual(progress.steps, 0)
        self.assertEqual(progress.steps_goal, 8000)
        self.assertEqual(progress.active_minutes, 0)
        self.assertEqual(progress.distance_km, 0.0)
        self.assertEqual(progress.activity_calories, 0.0)
        self.assertIsNone(progress.weight_kg)

    def test_unique_user_date_constraint(self):
        today = timezone.localdate()

        DailyProgress.objects.create(
            user=self.user,
            date=today
        )

        with self.assertRaises(Exception):
            DailyProgress.objects.create(
                user=self.user,
                date=today
            )

    def test_different_users_can_have_progress_on_same_date(self):
        second_user = User.objects.create_user(
            username="second_user",
            password="testpass123"
        )

        today = timezone.localdate()

        DailyProgress.objects.create(
            user=self.user,
            date=today
        )

        second_progress = DailyProgress.objects.create(
            user=second_user,
            date=today
        )

        self.assertEqual(
            DailyProgress.objects.filter(date=today).count(),
            2
        )

        self.assertEqual(second_progress.user, second_user)

    def test_string_representation(self):
        progress = DailyProgress.objects.create(
            user=self.user,
            date=timezone.localdate()
        )

        expected = (
            f"{self.user.username} - "
            f"{timezone.localdate()}"
        )

        self.assertEqual(str(progress), expected)

    def test_progress_ordering_by_latest_date(self):
        today = timezone.localdate()

        older = DailyProgress.objects.create(
            user=self.user,
            date=today - timedelta(days=2)
        )

        newer = DailyProgress.objects.create(
            user=self.user,
            date=today
        )

        records = list(DailyProgress.objects.all())

        self.assertEqual(records[0], newer)
        self.assertEqual(records[1], older)


# ============================================================
# PROGRESS PAGE TESTS
# ============================================================

class ProgressPageTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="page_user",
            password="testpass123"
        )

        self.url = reverse("progress:progress")

    def test_progress_page_requires_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_progress_page_loads_successfully(self):
        self.client.login(
            username="page_user",
            password="testpass123"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_progress_page_creates_today_record(self):
        self.client.login(
            username="page_user",
            password="testpass123"
        )

        today = timezone.localdate()

        self.assertFalse(
            DailyProgress.objects.filter(
                user=self.user,
                date=today
            ).exists()
        )

        self.client.get(self.url)

        self.assertTrue(
            DailyProgress.objects.filter(
                user=self.user,
                date=today
            ).exists()
        )

    def test_progress_page_does_not_create_duplicate_records(self):
        self.client.login(
            username="page_user",
            password="testpass123"
        )

        today = timezone.localdate()

        DailyProgress.objects.create(
            user=self.user,
            date=today,
            steps=2500
        )

        self.client.get(self.url)
        self.client.get(self.url)

        self.assertEqual(
            DailyProgress.objects.filter(
                user=self.user,
                date=today
            ).count(),
            1
        )

    def test_progress_page_displays_existing_steps(self):
        self.client.login(
            username="page_user",
            password="testpass123"
        )

        DailyProgress.objects.create(
            user=self.user,
            date=timezone.localdate(),
            steps=4000,
            steps_goal=8000
        )

        response = self.client.get(self.url)

        self.assertEqual(response.context["steps"], 4000)
        self.assertEqual(response.context["steps_goal"], 8000)
        self.assertEqual(response.context["step_percentage"], 50)

    def test_step_percentage_never_exceeds_100(self):
        self.client.login(
            username="page_user",
            password="testpass123"
        )

        DailyProgress.objects.create(
            user=self.user,
            date=timezone.localdate(),
            steps=12000,
            steps_goal=8000
        )

        response = self.client.get(self.url)

        self.assertEqual(
            response.context["step_percentage"],
            100
        )


# ============================================================
# PROGRESS SUMMARY API TESTS
# ============================================================

class ProgressSummaryAPITests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="api_user",
            password="testpass123"
        )

        self.url = reverse("progress:api_summary")

    def test_summary_api_requires_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)

        data = response.json()

        self.assertFalse(data["success"])

        self.assertEqual(
            data["message"],
            "Authentication required."
        )

    def test_summary_api_returns_default_values(self):
        self.client.login(
            username="api_user",
            password="testpass123"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["steps"], 0)
        self.assertEqual(data["steps_goal"], 8000)
        self.assertEqual(data["distance_km"], 0)
        self.assertEqual(data["active_minutes"], 0)
        self.assertEqual(data["calories_burned"], 0)
        self.assertIsNone(data["weight_kg"])
        self.assertEqual(data["weekly_progress"], [])

    def test_summary_api_returns_existing_progress(self):
        self.client.login(
            username="api_user",
            password="testpass123"
        )

        DailyProgress.objects.create(
            user=self.user,
            date=timezone.localdate(),
            steps=6000,
            steps_goal=10000,
            distance_km=4.2,
            active_minutes=45,
            activity_calories=230,
            weight_kg=65.5
        )

        response = self.client.get(self.url)

        data = response.json()

        self.assertEqual(data["steps"], 6000)
        self.assertEqual(data["steps_goal"], 10000)
        self.assertEqual(data["distance_km"], 4.2)
        self.assertEqual(data["active_minutes"], 45)
        self.assertEqual(data["calories_burned"], 230)
        self.assertEqual(data["weight_kg"], 65.5)

    def test_summary_api_returns_weekly_progress(self):
        self.client.login(
            username="api_user",
            password="testpass123"
        )

        today = timezone.localdate()

        DailyProgress.objects.create(
            user=self.user,
            date=today - timedelta(days=1),
            steps=3000,
            distance_km=2.1,
            active_minutes=20
        )

        DailyProgress.objects.create(
            user=self.user,
            date=today,
            steps=5000,
            distance_km=3.5,
            active_minutes=40
        )

        response = self.client.get(self.url)

        weekly = response.json()["weekly_progress"]

        self.assertEqual(len(weekly), 2)
        self.assertEqual(weekly[0]["steps"], 3000)
        self.assertEqual(weekly[1]["steps"], 5000)

    def test_summary_api_excludes_old_and_future_records(self):
        self.client.login(
            username="api_user",
            password="testpass123"
        )

        today = timezone.localdate()

        DailyProgress.objects.create(
            user=self.user,
            date=today - timedelta(days=10),
            steps=1000
        )

        DailyProgress.objects.create(
            user=self.user,
            date=today + timedelta(days=1),
            steps=9000
        )

        response = self.client.get(self.url)

        weekly = response.json()["weekly_progress"]

        self.assertEqual(len(weekly), 0)

    def test_summary_api_does_not_return_other_users_data(self):
        self.client.login(
            username="api_user",
            password="testpass123"
        )

        other_user = User.objects.create_user(
            username="other_user",
            password="testpass123"
        )

        DailyProgress.objects.create(
            user=other_user,
            date=timezone.localdate(),
            steps=15000
        )

        response = self.client.get(self.url)

        self.assertEqual(response.json()["steps"], 0)

    def test_summary_api_reflects_new_sensor_updates_immediately(self):
        self.client.login(
            username="api_user",
            password="testpass123"
        )

        DailyProgress.objects.create(
            user=self.user,
            date=timezone.localdate(),
            steps=1200,
            steps_goal=8000,
            distance_km=0.84,
            activity_calories=48
        )

        first_data = self.client.get(self.url).json()

        self.assertEqual(first_data["steps"], 1200)

        update_url = reverse("progress:update_steps")

        self.client.post(
            update_url,
            data=json.dumps({
                "steps_increment": 350
            }),
            content_type="application/json"
        )

        latest_data = self.client.get(self.url).json()

        self.assertEqual(latest_data["steps"], 1550)
        self.assertEqual(latest_data["distance_km"], 1.09)
        self.assertEqual(latest_data["calories_burned"], 62)


# ============================================================
# UPDATE STEPS API TESTS
# ============================================================

class UpdateStepsAPITests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="steps_user",
            password="testpass123"
        )

        self.url = reverse("progress:update_steps")

    def post_json(self, data):
        return self.client.post(
            self.url,
            data=json.dumps(data),
            content_type="application/json"
        )

    def test_update_steps_requires_login(self):
        response = self.post_json({
            "steps_increment": 1000
        })

        self.assertEqual(response.status_code, 302)

    def test_update_steps_only_accepts_post(self):
        self.client.login(
            username="steps_user",
            password="testpass123"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

    def test_update_steps_successfully(self):
        self.client.login(
            username="steps_user",
            password="testpass123"
        )

        response = self.post_json({
            "steps_increment": 1000
        })

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["steps"], 1000)
        self.assertEqual(data["goal"], 8000)
        self.assertEqual(data["step_percentage"], 13)
        self.assertEqual(data["distance"], 0.7)
        self.assertEqual(data["calories"], 40.0)

    def test_update_steps_accumulates_increment(self):
        self.client.login(
            username="steps_user",
            password="testpass123"
        )

        self.post_json({
            "steps_increment": 1000
        })

        response = self.post_json({
            "steps_increment": 2000
        })

        data = response.json()

        self.assertEqual(data["steps"], 3000)
        self.assertEqual(data["distance"], 2.1)
        self.assertEqual(data["calories"], 120.0)

    def test_sensor_style_small_updates_accumulate(self):
        self.client.login(
            username="steps_user",
            password="testpass123"
        )

        sensor_batches = [12, 8, 15, 20, 10]

        for batch in sensor_batches:

            response = self.post_json({
                "steps_increment": batch
            })

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["success"])

        progress = DailyProgress.objects.get(
            user=self.user,
            date=timezone.localdate()
        )

        self.assertEqual(
            progress.steps,
            sum(sensor_batches)
        )

        self.assertEqual(
            progress.distance_km,
            0.0455
        )

        self.assertEqual(
            progress.activity_calories,
            2.6
        )

    def test_update_steps_with_zero_increment(self):
        self.client.login(
            username="steps_user",
            password="testpass123"
        )

        response = self.post_json({
            "steps_increment": 0
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["steps"], 0)

    def test_update_steps_rejects_negative_increment(self):
        self.client.login(
            username="steps_user",
            password="testpass123"
        )

        response = self.post_json({
            "steps_increment": -100
        })

        self.assertEqual(response.status_code, 400)

    def test_update_steps_rejects_increment_above_limit(self):
        self.client.login(
            username="steps_user",
            password="testpass123"
        )

        response = self.post_json({
            "steps_increment": 100001
        })

        self.assertEqual(response.status_code, 400)

    def test_update_steps_rejects_invalid_number(self):
        self.client.login(
            username="steps_user",
            password="testpass123"
        )

        response = self.post_json({
            "steps_increment": "abc"
        })

        self.assertEqual(response.status_code, 400)

    def test_update_steps_rejects_invalid_json(self):
        self.client.login(
            username="steps_user",
            password="testpass123"
        )

        response = self.client.post(
            self.url,
            data="invalid json",
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

    def test_update_steps_rejects_non_dictionary_data(self):
        self.client.login(
            username="steps_user",
            password="testpass123"
        )

        response = self.client.post(
            self.url,
            data=json.dumps([1000, 2000]),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

    def test_update_steps_percentage_is_capped(self):
        self.client.login(
            username="steps_user",
            password="testpass123"
        )

        response = self.post_json({
            "steps_increment": 10000
        })

        self.assertEqual(
            response.json()["step_percentage"],
            100
        )

    def test_update_steps_creates_today_record(self):
        self.client.login(
            username="steps_user",
            password="testpass123"
        )

        today = timezone.localdate()

        response = self.post_json({
            "steps_increment": 500
        })

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            DailyProgress.objects.filter(
                user=self.user,
                date=today
            ).exists()
        )

    def test_sensor_updates_do_not_modify_another_users_progress(self):
        self.client.login(
            username="steps_user",
            password="testpass123"
        )

        other_user = User.objects.create_user(
            username="steps_other",
            password="testpass123"
        )

        other_progress = DailyProgress.objects.create(
            user=other_user,
            date=timezone.localdate(),
            steps=900
        )

        self.post_json({
            "steps_increment": 300
        })

        other_progress.refresh_from_db()

        self.assertEqual(other_progress.steps, 900)


# ============================================================
# UPDATE STEP GOAL API TESTS
# ============================================================

class UpdateStepGoalAPITests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="goal_user",
            password="testpass123"
        )

        self.url = reverse("progress:update_step_goal")

    def post_json(self, data):
        return self.client.post(
            self.url,
            data=json.dumps(data),
            content_type="application/json"
        )

    def test_update_goal_requires_login(self):
        response = self.post_json({
            "goal": 10000
        })

        self.assertEqual(response.status_code, 302)

    def test_update_goal_only_accepts_post(self):
        self.client.login(
            username="goal_user",
            password="testpass123"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

    def test_update_goal_successfully(self):
        self.client.login(
            username="goal_user",
            password="testpass123"
        )

        response = self.post_json({
            "goal": 10000
        })

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["goal"], 10000)
        self.assertEqual(data["steps"], 0)
        self.assertEqual(data["step_percentage"], 0)

    def test_update_goal_lower_boundary(self):
        self.client.login(
            username="goal_user",
            password="testpass123"
        )

        response = self.post_json({
            "goal": 1000
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["goal"], 1000)

    def test_update_goal_upper_boundary(self):
        self.client.login(
            username="goal_user",
            password="testpass123"
        )

        response = self.post_json({
            "goal": 50000
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["goal"], 50000)

    def test_update_goal_rejects_below_minimum(self):
        self.client.login(
            username="goal_user",
            password="testpass123"
        )

        response = self.post_json({
            "goal": 999
        })

        self.assertEqual(response.status_code, 400)

    def test_update_goal_rejects_above_maximum(self):
        self.client.login(
            username="goal_user",
            password="testpass123"
        )

        response = self.post_json({
            "goal": 50001
        })

        self.assertEqual(response.status_code, 400)

    def test_update_goal_rejects_invalid_value(self):
        self.client.login(
            username="goal_user",
            password="testpass123"
        )

        response = self.post_json({
            "goal": "abc"
        })

        self.assertEqual(response.status_code, 400)

    def test_update_goal_rejects_invalid_json(self):
        self.client.login(
            username="goal_user",
            password="testpass123"
        )

        response = self.client.post(
            self.url,
            data="invalid json",
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

    def test_update_goal_rejects_non_dictionary_data(self):
        self.client.login(
            username="goal_user",
            password="testpass123"
        )

        response = self.client.post(
            self.url,
            data=json.dumps([8000]),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

    def test_update_goal_calculates_percentage(self):
        self.client.login(
            username="goal_user",
            password="testpass123"
        )

        DailyProgress.objects.create(
            user=self.user,
            date=timezone.localdate(),
            steps=5000
        )

        response = self.post_json({
            "goal": 10000
        })

        self.assertEqual(
            response.json()["step_percentage"],
            50
        )

    def test_update_goal_does_not_reset_current_steps(self):
        self.client.login(
            username="goal_user",
            password="testpass123"
        )

        progress = DailyProgress.objects.create(
            user=self.user,
            date=timezone.localdate(),
            steps=4500,
            steps_goal=8000
        )

        response = self.post_json({
            "goal": 12000
        })

        progress.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(progress.steps, 4500)
        self.assertEqual(progress.steps_goal, 12000)


# ============================================================
# UPDATE WEIGHT API TESTS
# ============================================================

class UpdateWeightAPITests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="weight_user",
            password="testpass123"
        )

        self.url = reverse("progress:update_weight")

    def post_json(self, data):
        return self.client.post(
            self.url,
            data=json.dumps(data),
            content_type="application/json"
        )

    def test_update_weight_requires_login(self):
        response = self.post_json({
            "weight": 65
        })

        self.assertEqual(response.status_code, 302)

    def test_update_weight_only_accepts_post(self):
        self.client.login(
            username="weight_user",
            password="testpass123"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

    def test_update_weight_successfully(self):
        self.client.login(
            username="weight_user",
            password="testpass123"
        )

        response = self.post_json({
            "weight": 65.5
        })

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["weight"], 65.5)

        self.assertEqual(
            data["message"],
            "Weight saved successfully."
        )

    def test_update_weight_lower_boundary(self):
        self.client.login(
            username="weight_user",
            password="testpass123"
        )

        response = self.post_json({
            "weight": 20
        })

        self.assertEqual(response.status_code, 200)

    def test_update_weight_upper_boundary(self):
        self.client.login(
            username="weight_user",
            password="testpass123"
        )

        response = self.post_json({
            "weight": 300
        })

        self.assertEqual(response.status_code, 200)

    def test_update_weight_rejects_below_minimum(self):
        self.client.login(
            username="weight_user",
            password="testpass123"
        )

        response = self.post_json({
            "weight": 19.9
        })

        self.assertEqual(response.status_code, 400)

    def test_update_weight_rejects_above_maximum(self):
        self.client.login(
            username="weight_user",
            password="testpass123"
        )

        response = self.post_json({
            "weight": 300.1
        })

        self.assertEqual(response.status_code, 400)

    def test_update_weight_rejects_nan(self):
        self.client.login(
            username="weight_user",
            password="testpass123"
        )

        response = self.post_json({
            "weight": "NaN"
        })

        self.assertEqual(response.status_code, 400)

    def test_update_weight_rejects_infinity(self):
        self.client.login(
            username="weight_user",
            password="testpass123"
        )

        response = self.post_json({
            "weight": "Infinity"
        })

        self.assertEqual(response.status_code, 400)

    def test_update_weight_rejects_invalid_number(self):
        self.client.login(
            username="weight_user",
            password="testpass123"
        )

        response = self.post_json({
            "weight": "abc"
        })

        self.assertEqual(response.status_code, 400)

    def test_update_weight_rejects_invalid_json(self):
        self.client.login(
            username="weight_user",
            password="testpass123"
        )

        response = self.client.post(
            self.url,
            data="invalid json",
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

    def test_update_weight_rejects_non_dictionary_data(self):
        self.client.login(
            username="weight_user",
            password="testpass123"
        )

        response = self.client.post(
            self.url,
            data=json.dumps([65]),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

    def test_update_weight_saves_to_today_record(self):
        self.client.login(
            username="weight_user",
            password="testpass123"
        )

        today = timezone.localdate()

        response = self.post_json({
            "weight": 70.2
        })

        self.assertEqual(response.status_code, 200)

        progress = DailyProgress.objects.get(
            user=self.user,
            date=today
        )

        self.assertEqual(progress.weight_kg, 70.2)

    def test_update_weight_does_not_change_other_users_data(self):
        self.client.login(
            username="weight_user",
            password="testpass123"
        )

        other_user = User.objects.create_user(
            username="weight_other",
            password="testpass123"
        )

        other_progress = DailyProgress.objects.create(
            user=other_user,
            date=timezone.localdate(),
            weight_kg=80
        )

        self.post_json({
            "weight": 65
        })

        other_progress.refresh_from_db()

        self.assertEqual(other_progress.weight_kg, 80)