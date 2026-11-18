import base64
import io
import json
import tempfile

from unittest.mock import Mock, patch

from PIL import Image

from django.test import TestCase, override_settings
from django.urls import reverse

from django.contrib.auth.models import User
from nutrition.models import FoodScan, NutritionGoal, WaterIntake


def create_test_image():
    """Create a small valid image for testing."""
    image = Image.new("RGB", (10, 10), color="red")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return f"data:image/png;base64,{encoded}"


def valid_nutrition_data():
    return {
        "food_name": "Chicken Rice",
        "calories": 450,
        "protein": 30,
        "carbs": 50,
        "fat": 12,
        "fiber": 4,
        "sugar": 3,
        "ai_tip": "A balanced meal with good protein."
    }


class NutritionTestBase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="nutritionuser",
            password="TestPassword123"
        )

        self.scan_url = reverse("scan_food")
        self.page_url = reverse("nutrition_page")

        self.image_data = create_test_image()

        self.temp_media = tempfile.TemporaryDirectory()

        self.media_override = override_settings(
            MEDIA_ROOT=self.temp_media.name,
            GEMINI_API_KEY="test-api-key",
            GEMINI_MODEL="test-model"
        )

        self.media_override.enable()

    def tearDown(self):
        self.media_override.disable()
        self.temp_media.cleanup()

    def login(self):
        self.client.login(
            username="nutritionuser",
            password="TestPassword123"
        )

    def send_scan(self, payload=None):
        if payload is None:
            payload = {"image": self.image_data}

        return self.client.post(
            self.scan_url,
            data=json.dumps(payload),
            content_type="application/json"
        )


# ============================================================
# NUTRITION PAGE TESTS
# ============================================================

class NutritionPageTests(NutritionTestBase):

    def test_nutrition_page_opens(self):
        response = self.client.get(self.page_url)

        self.assertEqual(response.status_code, 200)

    def test_nutrition_page_uses_correct_template(self):
        response = self.client.get(self.page_url)

        self.assertTemplateUsed(
            response,
            "nutrition/nutrition.html"
        )

    def test_nutrition_page_allows_logged_in_user(self):
        self.login()

        response = self.client.get(self.page_url)

        self.assertEqual(response.status_code, 200)


# ============================================================
# FOOD SCAN AUTHENTICATION TESTS
# ============================================================

class FoodScanAuthenticationTests(NutritionTestBase):

    def test_scan_requires_login(self):
        response = self.send_scan()

        self.assertEqual(response.status_code, 401)

        data = response.json()

        self.assertFalse(data["success"])
        self.assertIn("sign in", data["error"].lower())

    def test_scan_accepts_logged_in_user(self):
        self.login()

        with patch("nutrition.views.genai.Client"), \
             patch("nutrition.views.fallback_chain") as fallback:

            fallback.return_value = (
                Mock(text=json.dumps(valid_nutrition_data())),
                "gemini"
            )

            response = self.send_scan()

        self.assertEqual(response.status_code, 200)


# ============================================================
# HTTP METHOD TESTS
# ============================================================

class FoodScanMethodTests(NutritionTestBase):

    def test_get_request_is_rejected(self):
        self.login()

        response = self.client.get(self.scan_url)

        self.assertEqual(response.status_code, 405)


# ============================================================
# REQUEST VALIDATION TESTS
# ============================================================

class FoodScanValidationTests(NutritionTestBase):

    def test_invalid_json_is_rejected(self):
        self.login()

        response = self.client.post(
            self.scan_url,
            data="{invalid json",
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

    def test_json_array_is_rejected(self):
        self.login()

        response = self.client.post(
            self.scan_url,
            data=json.dumps(["image"]),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

    def test_json_string_is_rejected(self):
        self.login()

        response = self.client.post(
            self.scan_url,
            data=json.dumps("hello"),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

    def test_missing_image_is_rejected(self):
        self.login()

        response = self.send_scan({})

        self.assertEqual(response.status_code, 400)

    def test_empty_image_is_rejected(self):
        self.login()

        response = self.send_scan({"image": ""})

        self.assertEqual(response.status_code, 400)

    def test_non_image_data_is_rejected(self):
        self.login()

        response = self.send_scan({
            "image": "not-an-image"
        })

        self.assertEqual(response.status_code, 400)

    def test_invalid_base64_is_rejected(self):
        self.login()

        response = self.send_scan({
            "image": "data:image/png;base64,%%%invalid%%%"
        })

        self.assertEqual(response.status_code, 400)

    def test_corrupted_image_is_rejected(self):
        self.login()

        fake_image = base64.b64encode(
            b"This is not a real image"
        ).decode()

        response = self.send_scan({
            "image": f"data:image/png;base64,{fake_image}"
        })

        self.assertEqual(response.status_code, 400)

    def test_image_without_base64_header_is_rejected(self):
        self.login()

        response = self.send_scan({
            "image": "data:image/png,invalid"
        })

        self.assertEqual(response.status_code, 400)


# ============================================================
# API CONFIGURATION TESTS
# ============================================================

class FoodScanConfigurationTests(NutritionTestBase):

    def test_missing_api_key_returns_503(self):
        self.login()

        with override_settings(GEMINI_API_KEY=None):

            response = self.send_scan()

        self.assertEqual(response.status_code, 503)

        self.assertFalse(response.json()["success"])

    def test_gemini_client_initialization_failure_returns_503(self):
        self.login()

        with patch(
            "nutrition.views.genai.Client",
            side_effect=Exception("Client initialization failed")
        ):

            response = self.send_scan()

        self.assertEqual(response.status_code, 503)

        self.assertFalse(response.json()["success"])


# ============================================================
# AI PROVIDER TESTS
# ============================================================

class FoodScanAITests(NutritionTestBase):

    def test_successful_gemini_response(self):
        self.login()

        nutrition = valid_nutrition_data()

        mock_response = Mock(
            text=json.dumps(nutrition)
        )

        with patch("nutrition.views.genai.Client"), \
             patch("nutrition.views.fallback_chain") as fallback:

            fallback.return_value = (
                mock_response,
                "gemini-test-model"
            )

            response = self.send_scan()

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(
            data["nutrition"]["food_name"],
            "Chicken Rice"
        )

        fallback.assert_called_once()

    def test_groq_response_format_is_supported(self):
        self.login()

        nutrition = valid_nutrition_data()

        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(nutrition)
                    }
                }
            ]
        }

        with patch("nutrition.views.genai.Client"), \
             patch("nutrition.views.fallback_chain") as fallback:

            fallback.return_value = (
                mock_response,
                "groq"
            )

            response = self.send_scan()

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.json()["nutrition"]["food_name"],
            "Chicken Rice"
        )

    def test_openai_response_format_is_supported(self):
        self.login()

        nutrition = valid_nutrition_data()

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = json.dumps(nutrition)

        with patch("nutrition.views.genai.Client"), \
             patch("nutrition.views.fallback_chain") as fallback:

            fallback.return_value = (
                mock_response,
                "openai"
            )

            response = self.send_scan()

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.json()["nutrition"]["food_name"],
            "Chicken Rice"
        )

    def test_all_ai_providers_failing_returns_503(self):
        self.login()

        with patch("nutrition.views.genai.Client"), \
             patch(
                 "nutrition.views.fallback_chain",
                 side_effect=Exception("All providers failed")
             ):

            response = self.send_scan()

        self.assertEqual(response.status_code, 503)

        self.assertFalse(response.json()["success"])

    def test_invalid_ai_json_returns_502(self):
        self.login()

        mock_response = Mock(
            text="This is not JSON"
        )

        with patch("nutrition.views.genai.Client"), \
             patch("nutrition.views.fallback_chain") as fallback:

            fallback.return_value = (
                mock_response,
                "gemini"
            )

            response = self.send_scan()

        self.assertEqual(response.status_code, 502)

        self.assertFalse(response.json()["success"])

    def test_ai_response_with_missing_nutrition_values_returns_502(self):
        self.login()

        incomplete_data = {
            "food_name": "Rice",
            "calories": 200
        }

        mock_response = Mock(
            text=json.dumps(incomplete_data)
        )

        with patch("nutrition.views.genai.Client"), \
             patch("nutrition.views.fallback_chain") as fallback:

            fallback.return_value = (
                mock_response,
                "gemini"
            )

            response = self.send_scan()

        self.assertEqual(response.status_code, 502)

    def test_ai_response_with_negative_calories_returns_502(self):
        self.login()

        nutrition = valid_nutrition_data()
        nutrition["calories"] = -100

        mock_response = Mock(
            text=json.dumps(nutrition)
        )

        with patch("nutrition.views.genai.Client"), \
             patch("nutrition.views.fallback_chain") as fallback:

            fallback.return_value = (
                mock_response,
                "gemini"
            )

            response = self.send_scan()

        self.assertEqual(response.status_code, 502)

    def test_ai_response_with_nan_value_returns_502(self):
        self.login()

        nutrition = valid_nutrition_data()
        nutrition["protein"] = float("nan")

        mock_response = Mock(
            text=json.dumps(nutrition)
        )

        with patch("nutrition.views.genai.Client"), \
             patch("nutrition.views.fallback_chain") as fallback:

            fallback.return_value = (
                mock_response,
                "gemini"
            )

            response = self.send_scan()

        self.assertEqual(response.status_code, 502)

    def test_food_name_defaults_when_missing(self):
        self.login()

        nutrition = valid_nutrition_data()
        nutrition["food_name"] = ""

        mock_response = Mock(
            text=json.dumps(nutrition)
        )

        with patch("nutrition.views.genai.Client"), \
             patch("nutrition.views.fallback_chain") as fallback:

            fallback.return_value = (
                mock_response,
                "gemini"
            )

            response = self.send_scan()

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.json()["nutrition"]["food_name"],
            "Scanned meal"
        )

    def test_food_name_is_limited_to_100_characters(self):
        self.login()

        nutrition = valid_nutrition_data()
        nutrition["food_name"] = "A" * 150

        mock_response = Mock(
            text=json.dumps(nutrition)
        )

        with patch("nutrition.views.genai.Client"), \
             patch("nutrition.views.fallback_chain") as fallback:

            fallback.return_value = (
                mock_response,
                "gemini"
            )

            response = self.send_scan()

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            len(response.json()["nutrition"]["food_name"]),
            100
        )


# ============================================================
# DATABASE TESTS
# ============================================================

class FoodScanDatabaseTests(NutritionTestBase):

    def test_successful_scan_saves_food_to_database(self):
        self.login()

        nutrition = valid_nutrition_data()

        mock_response = Mock(
            text=json.dumps(nutrition)
        )

        with patch("nutrition.views.genai.Client"), \
             patch("nutrition.views.fallback_chain") as fallback:

            fallback.return_value = (
                mock_response,
                "gemini"
            )

            response = self.send_scan()

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            FoodScan.objects.filter(user=self.user).count(),
            1
        )

        food = FoodScan.objects.get(user=self.user)

        self.assertEqual(food.food_name, "Chicken Rice")
        self.assertEqual(food.calories, 450)
        self.assertEqual(food.protein, 30)
        self.assertEqual(food.carbohydrates, 50)
        self.assertEqual(food.fats, 12)
        self.assertEqual(food.fiber, 4)
        self.assertEqual(food.quantity, "1 serving")
        self.assertTrue(food.is_consumed)

    def test_food_scan_is_saved_with_image(self):
        self.login()

        mock_response = Mock(
            text=json.dumps(valid_nutrition_data())
        )

        with patch("nutrition.views.genai.Client"), \
             patch("nutrition.views.fallback_chain") as fallback:

            fallback.return_value = (
                mock_response,
                "gemini"
            )

            response = self.send_scan()

        self.assertEqual(response.status_code, 200)

        food = FoodScan.objects.get(user=self.user)

        self.assertTrue(food.image)
        self.assertTrue(food.image.name.endswith(".jpg"))

        with food.image.open("rb") as saved_image:
            image = Image.open(saved_image)
            image.verify()

    def test_scan_is_not_saved_when_ai_fails(self):
        self.login()

        with patch("nutrition.views.genai.Client"), \
             patch(
                 "nutrition.views.fallback_chain",
                 side_effect=Exception("AI failure")
             ):

            response = self.send_scan()

        self.assertEqual(response.status_code, 503)

        self.assertEqual(
            FoodScan.objects.filter(user=self.user).count(),
            0
        )

    def test_scan_is_not_saved_when_ai_data_is_invalid(self):
        self.login()

        mock_response = Mock(
            text="Invalid AI data"
        )

        with patch("nutrition.views.genai.Client"), \
             patch("nutrition.views.fallback_chain") as fallback:

            fallback.return_value = (
                mock_response,
                "gemini"
            )

            response = self.send_scan()

        self.assertEqual(response.status_code, 502)

        self.assertEqual(
            FoodScan.objects.filter(user=self.user).count(),
            0
        )

    def test_food_scan_belongs_to_correct_user(self):
        self.login()

        mock_response = Mock(
            text=json.dumps(valid_nutrition_data())
        )

        with patch("nutrition.views.genai.Client"), \
             patch("nutrition.views.fallback_chain") as fallback:

            fallback.return_value = (
                mock_response,
                "gemini"
            )

            self.send_scan()

        food = FoodScan.objects.first()

        self.assertEqual(food.user, self.user)


# ============================================================
# NUTRITION MODEL TESTS
# ============================================================

class NutritionModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="modeluser",
            password="TestPassword123"
        )

    def test_nutrition_goal_creation(self):
        goal = NutritionGoal.objects.create(
            user=self.user,
            calories_target=2200,
            protein_target=120,
            carbs_target=250,
            fat_target=70
        )

        self.assertEqual(goal.user, self.user)
        self.assertEqual(goal.calories_target, 2200)

    def test_nutrition_goal_string_representation(self):
        goal = NutritionGoal.objects.create(
            user=self.user,
            calories_target=2200,
            protein_target=120,
            carbs_target=250,
            fat_target=70
        )

        self.assertEqual(str(goal), "modeluser")

    def test_user_can_only_have_one_nutrition_goal(self):
        NutritionGoal.objects.create(
            user=self.user,
            calories_target=2200,
            protein_target=120,
            carbs_target=250,
            fat_target=70
        )

        with self.assertRaises(Exception):
            NutritionGoal.objects.create(
                user=self.user,
                calories_target=2000,
                protein_target=100,
                carbs_target=200,
                fat_target=60
            )

    def test_water_intake_creation(self):
        water = WaterIntake.objects.create(
            user=self.user,
            water_amount=0.5
        )

        self.assertEqual(water.user, self.user)
        self.assertEqual(water.water_amount, 0.5)
        self.assertEqual(water.target_amount, 3)

    def test_water_target_can_be_changed(self):
        water = WaterIntake.objects.create(
            user=self.user,
            water_amount=1,
            target_amount=4
        )

        self.assertEqual(water.target_amount, 4)

    def test_food_scan_user_relationship(self):
        food = FoodScan.objects.create(
            user=self.user,
            food_name="Apple",
            calories=95,
            protein=0.5,
            carbohydrates=25,
            fats=0.3,
            fiber=4,
            quantity="1 apple",
            is_consumed=True
        )

        self.assertEqual(food.user, self.user)
        self.assertEqual(food.food_name, "Apple")

    def test_deleting_user_deletes_food_scans(self):
        FoodScan.objects.create(
            user=self.user,
            food_name="Apple",
            calories=95,
            protein=0.5,
            carbohydrates=25,
            fats=0.3,
            fiber=4,
            quantity="1 apple"
        )

        self.user.delete()

        self.assertEqual(FoodScan.objects.count(), 0)

    def test_deleting_user_deletes_nutrition_goal(self):
        NutritionGoal.objects.create(
            user=self.user,
            calories_target=2200,
            protein_target=120,
            carbs_target=250,
            fat_target=70
        )

        self.user.delete()

        self.assertEqual(NutritionGoal.objects.count(), 0)

    def test_deleting_user_deletes_water_intake(self):
        WaterIntake.objects.create(
            user=self.user,
            water_amount=1
        )

        self.user.delete()

        self.assertEqual(WaterIntake.objects.count(), 0)

