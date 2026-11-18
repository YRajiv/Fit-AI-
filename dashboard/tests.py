from datetime import timedelta
import json
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Dashboard
from .views import (
    get_today_datetime_range,
    parse_stored_data,
    normalize_diet_meals,
    retrieve_fitness_knowledge,
)

User = get_user_model()


class DashboardHelperTests(TestCase):

    def test_parse_valid_json(self):
        data = '{"calories": 500, "protein": 25}'

        result = parse_stored_data(data)

        self.assertEqual(result["calories"], 500)
        self.assertEqual(result["protein"], 25)

    def test_parse_invalid_data_returns_empty_dictionary(self):
        result = parse_stored_data("invalid json data")

        self.assertEqual(result, {})

    def test_parse_dictionary_returns_dictionary(self):
        data = {"calories": 300}

        result = parse_stored_data(data)

        self.assertEqual(result, data)

    def test_normalize_diet_meals_with_dictionary(self):
        meals = [
            {
                "meal": "Breakfast",
                "food": "Eggs",
                "calories": 250,
                "protein": 15,
            }
        ]

        result = normalize_diet_meals(meals)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["meal"], "Breakfast")
        self.assertEqual(result[0]["food"], "Eggs")

    def test_normalize_diet_meals_with_json_string(self):
        meals = [
            '{"meal": "Lunch", "food": "Rice", "calories": 400}'
        ]

        result = normalize_diet_meals(meals)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["meal"], "Lunch")
        self.assertEqual(result[0]["food"], "Rice")

    def test_today_datetime_range(self):
        today, tomorrow, today_start, tomorrow_start = (
            get_today_datetime_range()
        )

        self.assertEqual(tomorrow, today + timedelta(days=1))
        self.assertEqual(today_start.date(), today)
        self.assertEqual(tomorrow_start.date(), tomorrow)
        self.assertEqual(today_start.hour, 0)
        self.assertEqual(tomorrow_start.hour, 0)

    def test_fitness_knowledge_retrieval(self):
        result = retrieve_fitness_knowledge("How much protein should I eat?")

        self.assertIsNotNone(result)
        self.assertNotEqual(result, "")


class DashboardViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="dashboard_test",
            password="TestPassword123!",
        )

        self.dashboard_url = reverse("dashboard:home")
        self.summary_url = reverse("dashboard:api_summary")
        self.water_url = reverse("dashboard:add_water_quick")
        self.chat_url = reverse("dashboard:send_message")
        self.clear_chat_url = reverse("dashboard:clear_chat")

    def test_dashboard_requires_login(self):
        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, 302)

    def test_dashboard_loads_for_logged_in_user(self):
        self.client.login(
            username="dashboard_test",
            password="TestPassword123!",
        )

        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, 200)

    def test_dashboard_summary_requires_login(self):
        response = self.client.get(self.summary_url)

        self.assertEqual(response.status_code, 401)

    def test_dashboard_summary_returns_json_for_logged_in_user(self):
        self.client.login(
            username="dashboard_test",
            password="TestPassword123!",
        )

        response = self.client.get(self.summary_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        data = response.json()

        self.assertIn("success", data)
        self.assertIn("steps", data)
        self.assertIn("steps_goal", data)
        self.assertIn("water_amount", data)
        self.assertIn("consumed_calories", data)

    def test_dashboard_summary_rejects_post_request(self):
        self.client.login(
            username="dashboard_test",
            password="TestPassword123!",
        )

        response = self.client.post(self.summary_url)

        self.assertEqual(response.status_code, 405)

    def test_water_add_requires_login(self):
        response = self.client.post(
            self.water_url,
            {"amount": "0.5"},
        )

        self.assertEqual(response.status_code, 302)

    def test_add_water_with_valid_amount(self):
        self.client.login(
            username="dashboard_test",
            password="TestPassword123!",
        )

        response = self.client.post(
            self.water_url,
            {"amount": "0.5"},
        )

        self.assertEqual(response.status_code, 302)

        from nutrition.models import WaterIntake

        today = timezone.localdate()

        water = WaterIntake.objects.filter(
            user=self.user,
            date=today,
        ).first()

        self.assertIsNotNone(water)
        self.assertAlmostEqual(water.water_amount, 0.5)

    def test_invalid_water_amount_does_not_add_water(self):
        self.client.login(
            username="dashboard_test",
            password="TestPassword123!",
        )

        response = self.client.post(
            self.water_url,
            {"amount": "5"},
        )

        self.assertEqual(response.status_code, 302)

        from nutrition.models import WaterIntake

        today = timezone.localdate()

        water = WaterIntake.objects.filter(
            user=self.user,
            date=today,
        ).first()

        self.assertIsNone(water)

    def test_chat_requires_login(self):
        response = self.client.post(
            self.chat_url,
            data=json.dumps({"message": "Hello"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 302)

    def test_chat_rejects_empty_message(self):
        self.client.login(
            username="dashboard_test",
            password="TestPassword123!",
        )

        response = self.client.post(
            self.chat_url,
            data=json.dumps({"message": ""}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_chat_rejects_long_message(self):
        self.client.login(
            username="dashboard_test",
            password="TestPassword123!",
        )

        long_message = "a" * 2001

        response = self.client.post(
            self.chat_url,
            data=json.dumps({"message": long_message}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    @patch("dashboard.views.requests.post")
    def test_chat_success_without_real_ai_service(self, mock_post):
        self.client.login(
            username="dashboard_test",
            password="TestPassword123!",
        )

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "message": {
                "content": "Drink enough water and exercise regularly."
            }
        }

        mock_post.return_value = mock_response

        response = self.client.post(
            self.chat_url,
            data=json.dumps(
                {"message": "How can I stay healthy?"}
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertIn("reply", data)
        self.assertIn("water", data["reply"].lower())

        mock_post.assert_called_once()

    def test_clear_chat_requires_login(self):
        response = self.client.post(self.clear_chat_url)

        self.assertEqual(response.status_code, 302)

    def test_clear_chat_history(self):
        self.client.login(
            username="dashboard_test",
            password="TestPassword123!",
        )

        session = self.client.session

        session["fitai_chat_history"] = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]

        session.save()

        response = self.client.post(self.clear_chat_url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        self.assertNotIn(
            "fitai_chat_history",
            self.client.session,
        )
