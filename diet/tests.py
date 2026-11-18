import json

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from diet.models import UserFitnessProfile, WeeklyDietPlan
from diet.views import calculate_bmi


class DietBMICalculationTests(TestCase):
    """Tests for BMI calculation and BMI category."""

    def test_underweight_bmi(self):
        profile = UserFitnessProfile(height_cm=170, weight_kg=50)
        result = calculate_bmi(profile)

        self.assertEqual(result["bmi"], 17.3)
        self.assertEqual(result["bmi_category"], "Underweight")

    def test_normal_weight_bmi(self):
        profile = UserFitnessProfile(height_cm=170, weight_kg=70)
        result = calculate_bmi(profile)

        self.assertEqual(result["bmi"], 24.2)
        self.assertEqual(result["bmi_category"], "Normal weight")

    def test_overweight_bmi(self):
        profile = UserFitnessProfile(height_cm=170, weight_kg=80)
        result = calculate_bmi(profile)

        self.assertEqual(result["bmi"], 27.7)
        self.assertEqual(result["bmi_category"], "Overweight")

    def test_obese_bmi(self):
        profile = UserFitnessProfile(height_cm=170, weight_kg=90)
        result = calculate_bmi(profile)

        self.assertEqual(result["bmi"], 31.1)
        self.assertEqual(result["bmi_category"], "Obese")

    def test_bmi_rejects_zero_height(self):
        profile = UserFitnessProfile(height_cm=0, weight_kg=70)

        with self.assertRaises(ValueError):
            calculate_bmi(profile)

    def test_bmi_rejects_zero_weight(self):
        profile = UserFitnessProfile(height_cm=170, weight_kg=0)

        with self.assertRaises(ValueError):
            calculate_bmi(profile)


class DietOnboardingTests(TestCase):
    """Tests for the diet onboarding page."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="dietuser",
            password="TestPassword123"
        )

    def test_onboarding_requires_login(self):
        response = self.client.get(reverse("onboarding"))

        self.assertEqual(response.status_code, 302)

    def test_logged_in_user_can_open_onboarding(self):
        self.client.login(
            username="dietuser",
            password="TestPassword123"
        )

        response = self.client.get(reverse("onboarding"))

        self.assertEqual(response.status_code, 200)


class SaveDietProfileAPITests(TestCase):
    """Tests for saving height and weight."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="profileuser",
            password="TestPassword123"
        )

        self.client.login(
            username="profileuser",
            password="TestPassword123"
        )

        self.url = reverse("save_profile_api")

    def post_json(self, data):
        return self.client.post(
            self.url,
            data=json.dumps(data),
            content_type="application/json"
        )

    def test_save_profile_successfully(self):
        response = self.post_json({
            "height": 170,
            "weight": 70
        })

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["bmi"], 24.2)
        self.assertEqual(data["bmi_category"], "Normal weight")

        profile = UserFitnessProfile.objects.get(user=self.user)

        self.assertEqual(profile.height_cm, 170)
        self.assertEqual(profile.weight_kg, 70)

    def test_save_profile_creates_only_one_profile(self):
        self.post_json({
            "height": 170,
            "weight": 70
        })

        self.post_json({
            "height": 175,
            "weight": 75
        })

        self.assertEqual(
            UserFitnessProfile.objects.filter(user=self.user).count(),
            1
        )

    def test_save_profile_updates_existing_profile(self):
        UserFitnessProfile.objects.create(
            user=self.user,
            height_cm=170,
            weight_kg=70
        )

        response = self.post_json({
            "height": 180,
            "weight": 80
        })

        self.assertEqual(response.status_code, 200)

        profile = UserFitnessProfile.objects.get(user=self.user)

        self.assertEqual(profile.height_cm, 180)
        self.assertEqual(profile.weight_kg, 80)

    def test_updating_profile_deletes_old_diet_plans(self):
        UserFitnessProfile.objects.create(
            user=self.user,
            height_cm=170,
            weight_kg=70
        )

        WeeklyDietPlan.objects.create(
            user=self.user,
            plan_json={"old_plan": True}
        )

        response = self.post_json({
            "height": 175,
            "weight": 75
        })

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            WeeklyDietPlan.objects.filter(user=self.user).exists()
        )

    def test_save_profile_requires_login(self):
        self.client.logout()

        response = self.post_json({
            "height": 170,
            "weight": 70
        })

        self.assertEqual(response.status_code, 302)

    def test_get_request_is_rejected(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

    def test_invalid_json_is_rejected(self):
        response = self.client.post(
            self.url,
            data="{invalid json}",
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_missing_height_is_rejected(self):
        response = self.post_json({
            "weight": 70
        })

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_missing_weight_is_rejected(self):
        response = self.post_json({
            "height": 170
        })

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_zero_height_is_rejected(self):
        response = self.post_json({
            "height": 0,
            "weight": 70
        })

        self.assertEqual(response.status_code, 400)

    def test_zero_weight_is_rejected(self):
        response = self.post_json({
            "height": 170,
            "weight": 0
        })

        self.assertEqual(response.status_code, 400)

    def test_negative_height_is_rejected(self):
        response = self.post_json({
            "height": -170,
            "weight": 70
        })

        self.assertEqual(response.status_code, 400)

    def test_negative_weight_is_rejected(self):
        response = self.post_json({
            "height": 170,
            "weight": -70
        })

        self.assertEqual(response.status_code, 400)

    def test_height_below_minimum_is_rejected(self):
        response = self.post_json({
            "height": 49,
            "weight": 70
        })

        self.assertEqual(response.status_code, 400)

    def test_height_above_maximum_is_rejected(self):
        response = self.post_json({
            "height": 251,
            "weight": 70
        })

        self.assertEqual(response.status_code, 400)

    def test_weight_below_minimum_is_rejected(self):
        response = self.post_json({
            "height": 170,
            "weight": 9
        })

        self.assertEqual(response.status_code, 400)

    def test_weight_above_maximum_is_rejected(self):
        response = self.post_json({
            "height": 170,
            "weight": 301
        })

        self.assertEqual(response.status_code, 400)

    def test_minimum_valid_height_and_weight(self):
        response = self.post_json({
            "height": 50,
            "weight": 10
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_maximum_valid_height_and_weight(self):
        response = self.post_json({
            "height": 250,
            "weight": 300
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])


class BodyFatAnalysisAPITests(TestCase):
    """Tests for the retired body-fat analysis API."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="bodyfatuser",
            password="TestPassword123"
        )

        self.client.login(
            username="bodyfatuser",
            password="TestPassword123"
        )

        self.url = reverse("analyze_body_fat_api")

    def test_body_fat_api_returns_gone_status(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 410)

        data = response.json()

        self.assertFalse(data["success"])
        self.assertIn("no longer used", data["error"].lower())

    def test_body_fat_api_requires_login(self):
        self.client.logout()

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 302)


class DietPlanAPITests(TestCase):
    """Tests for the diet plan API."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="planuser",
            password="TestPassword123"
        )

        self.url = reverse("diet_plan_api")

    def test_diet_plan_api_requires_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)

        self.assertFalse(response.json()["success"])

    def test_diet_plan_api_without_profile(self):
        self.client.login(
            username="planuser",
            password="TestPassword123"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertFalse(data["has_profile"])
        self.assertIsNone(data["profile"])
        self.assertIsNone(data["weekly_plan"])


class DietDashboardTests(TestCase):
    """Tests for the main diet dashboard."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="dashboarddietuser",
            password="TestPassword123"
        )

        self.url = reverse("diet_dashboard")

    def test_diet_dashboard_requires_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_user_without_profile_is_redirected_to_onboarding(self):
        self.client.login(
            username="dashboarddietuser",
            password="TestPassword123"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("onboarding"),
            fetch_redirect_response=False
        )

