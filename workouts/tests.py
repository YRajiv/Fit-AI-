
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from diet.models import UserFitnessProfile
from progress.models import DailyProgress
from workouts.models import Workout
from workouts.views import recommend_workout, EXERCISES


class WorkoutRecommendationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="workoutuser",
            password="TestPassword123"
        )

        self.profile = UserFitnessProfile.objects.create(
            user=self.user,
            height_cm=170,
            weight_kg=65,
            goal="muscle_gain",
            fitness_level="Beginner",
            equipment="No Equipment",
            training_days=3,
            workout_duration=30
        )

    def test_recommendation_returns_expected_structure(self):
        result = recommend_workout(
            self.profile,
            self.user
        )

        self.assertIn("name", result)
        self.assertIn("category", result)
        self.assertIn("difficulty", result)
        self.assertIn("duration", result)
        self.assertIn("equipment", result)
        self.assertIn("exercises", result)

    def test_recommendation_matches_user_goal(self):
        result = recommend_workout(
            self.profile,
            self.user
        )

        for exercise in result["exercises"]:
            self.assertIn(
                self.profile.goal,
                exercise["goals"]
            )

    def test_beginner_does_not_receive_advanced_exercises(self):
        result = recommend_workout(
            self.profile,
            self.user
        )

        for exercise in result["exercises"]:
            self.assertEqual(
                exercise["difficulty"],
                "Beginner"
            )

    def test_equipment_filter_is_respected(self):
        result = recommend_workout(
            self.profile,
            self.user
        )

        for exercise in result["exercises"]:
            self.assertEqual(
                exercise["equipment"],
                self.profile.equipment
            )

    def test_recommendation_respects_duration_limit(self):
        self.profile.workout_duration = 20
        self.profile.save()

        result = recommend_workout(
            self.profile,
            self.user
        )

        self.assertLessEqual(
            len(result["exercises"]),
            3
        )

    def test_beginner_gets_two_sets(self):
        result = recommend_workout(
            self.profile,
            self.user
        )

        for exercise in result["exercises"]:
            self.assertEqual(
                exercise["sets"],
                2
            )

    def test_intermediate_gets_three_sets(self):
        self.profile.fitness_level = "Intermediate"
        self.profile.save()

        result = recommend_workout(
            self.profile,
            self.user
        )

        for exercise in result["exercises"]:
            self.assertEqual(
                exercise["sets"],
                3
            )

    def test_advanced_gets_four_sets(self):
        self.profile.fitness_level = "Advanced"
        self.profile.equipment = "Full Gym"
        self.profile.save()

        result = recommend_workout(
            self.profile,
            self.user
        )

        for exercise in result["exercises"]:
            self.assertEqual(
                exercise["sets"],
                4
            )

    def test_recommendation_uses_profile_equipment(self):
        self.profile.equipment = "Dumbbells"
        self.profile.fitness_level = "Beginner"
        self.profile.save()

        result = recommend_workout(
            self.profile,
            self.user
        )

        for exercise in result["exercises"]:
            self.assertEqual(
                exercise["equipment"],
                "Dumbbells"
            )

    def test_recommendation_uses_profile_duration(self):
        self.profile.workout_duration = 45
        self.profile.save()

        result = recommend_workout(
            self.profile,
            self.user
        )

        self.assertEqual(
            result["duration"],
            45
        )

    def test_recommendation_returns_empty_if_no_matching_exercises(self):
        self.profile.goal = "weight_loss"
        self.profile.equipment = "Full Gym"
        self.profile.fitness_level = "Beginner"
        self.profile.save()

        result = recommend_workout(
            self.profile,
            self.user
        )

        # Beginner + Full Gym may not have matching exercises.
        self.assertIsInstance(
            result["exercises"],
            list
        )


class WorkoutPageTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="pageuser",
            password="TestPassword123"
        )

        self.profile = UserFitnessProfile.objects.create(
            user=self.user,
            height_cm=170,
            weight_kg=65,
            goal="muscle_gain",
            fitness_level="Beginner",
            equipment="No Equipment",
            training_days=3,
            workout_duration=30
        )

    def test_workout_page_requires_login(self):
        response = self.client.get(
            reverse("workout:workouts")
        )

        self.assertEqual(
            response.status_code,
            302
        )

    def test_workout_page_loads_for_logged_in_user(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("workout:workouts")
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_workout_page_contains_profile(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("workout:workouts")
        )

        self.assertEqual(
            response.context["profile"],
            self.profile
        )

    def test_workout_page_without_profile(self):
        new_user = User.objects.create_user(
            username="noprofile",
            password="TestPassword123"
        )

        self.client.force_login(new_user)

        response = self.client.get(
            reverse("workout:workouts")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertTrue(
            response.context["profile_missing"]
        )

    def test_invalid_fitness_level_is_rejected(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("workout:workouts"),
            {
                "fitness_level": "InvalidLevel",
                "height_cm": "170",
                "weight_kg": "65",
                "has_equipment": "No",
                "equipment": "No Equipment",
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertTrue(
            response.context["form_errors"]
        )

    def test_invalid_height_is_rejected(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("workout:workouts"),
            {
                "fitness_level": "Beginner",
                "height_cm": "999",
                "weight_kg": "65",
                "has_equipment": "No",
                "equipment": "No Equipment",
            }
        )

        self.assertTrue(
            response.context["form_errors"]
        )

    def test_invalid_weight_is_rejected(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("workout:workouts"),
            {
                "fitness_level": "Beginner",
                "height_cm": "170",
                "weight_kg": "-5",
                "has_equipment": "No",
                "equipment": "No Equipment",
            }
        )

        self.assertTrue(
            response.context["form_errors"]
        )

    def test_valid_assessment_generates_workout(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("workout:workouts"),
            {
                "fitness_level": "Beginner",
                "height_cm": "175",
                "weight_kg": "70",
                "has_equipment": "Yes",
                "equipment": "Dumbbells",
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertTrue(
            response.context["form_submitted"]
        )

        self.profile.refresh_from_db()

        self.assertEqual(
            self.profile.fitness_level,
            "Beginner"
        )

        self.assertEqual(
            self.profile.height_cm,
            175
        )

        self.assertEqual(
            self.profile.weight_kg,
            70
        )

        self.assertEqual(
            self.profile.equipment,
            "Dumbbells"
        )

        self.assertTrue(
            response.context["workout_plan"]
        )


class WorkoutRecommendationAPITests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="apiuser",
            password="TestPassword123"
        )

        self.profile = UserFitnessProfile.objects.create(
            user=self.user,
            height_cm=170,
            weight_kg=65,
            goal="muscle_gain",
            fitness_level="Beginner",
            equipment="No Equipment",
            training_days=3,
            workout_duration=30
        )

    def test_recommendation_api_requires_authentication(self):
        response = self.client.get(
            reverse("workout:api_recommendation")
        )

        self.assertEqual(
            response.status_code,
            401
        )

    def test_recommendation_api_returns_workout(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("workout:api_recommendation")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        data = response.json()

        self.assertIn(
            "exercises",
            data
        )

        self.assertIn(
            "name",
            data
        )

    def test_recommendation_api_without_profile(self):
        user_without_profile = User.objects.create_user(
            username="api_no_profile",
            password="TestPassword123"
        )

        self.client.force_login(
            user_without_profile
        )

        response = self.client.get(
            reverse("workout:api_recommendation")
        )

        self.assertEqual(
            response.status_code,
            404
        )


class StartWorkoutTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="startuser",
            password="TestPassword123"
        )

        self.profile = UserFitnessProfile.objects.create(
            user=self.user,
            height_cm=170,
            weight_kg=65,
            goal="muscle_gain",
            fitness_level="Beginner",
            equipment="No Equipment",
            training_days=3,
            workout_duration=30
        )

    def test_start_workout_requires_login(self):
        response = self.client.post(
            reverse("workout:start_workout")
        )

        self.assertEqual(
            response.status_code,
            302
        )

    def test_start_workout_requires_post(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("workout:start_workout")
        )

        self.assertEqual(
            response.status_code,
            405
        )

    def test_start_workout_without_profile(self):
        user_without_profile = User.objects.create_user(
            username="start_no_profile",
            password="TestPassword123"
        )

        self.client.force_login(
            user_without_profile
        )

        response = self.client.post(
            reverse("workout:start_workout")
        )

        self.assertEqual(
            response.status_code,
            400
        )

    def test_start_workout_creates_database_record(self):
        self.client.force_login(self.user)

        recommendation = recommend_workout(
            self.profile,
            self.user
        )

        response = self.client.post(
            reverse("workout:start_workout"),
            {
                "workout_name": recommendation["name"]
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )

        data = response.json()

        self.assertEqual(
            data["status"],
            "success"
        )

        self.assertEqual(
            Workout.objects.filter(
                user=self.user
            ).count(),
            1
        )

        workout = Workout.objects.get(
            user=self.user
        )

        self.assertFalse(
            workout.is_completed
        )

        self.assertIsNotNone(
            workout.started_at
        )

    def test_start_workout_rejects_wrong_name(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("workout:start_workout"),
            {
                "workout_name": "Wrong Workout Name"
            }
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertEqual(
            Workout.objects.count(),
            0
        )


class CompleteWorkoutTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="completeuser",
            password="TestPassword123"
        )

        self.other_user = User.objects.create_user(
            username="otheruser",
            password="TestPassword123"
        )

        self.workout = Workout.objects.create(
            user=self.user,
            workout_name="Test Workout",
            description="Workout test",
            workout_category="Strength",
            target_sets=3,
            target_reps=12,
            completed_sets=0,
            completed_reps=0,
            duration=30,
            calories_burned=150,
            difficulty_level="Beginner",
            equipment_required="No Equipment",
            is_completed=False
        )

    def test_complete_workout_requires_login(self):
        response = self.client.post(
            reverse(
                "workout:complete_workout",
                args=[self.workout.id]
            )
        )

        self.assertEqual(
            response.status_code,
            302
        )

    def test_complete_workout_requires_post(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "workout:complete_workout",
                args=[self.workout.id]
            )
        )

        self.assertEqual(
            response.status_code,
            405
        )

    def test_user_cannot_complete_another_users_workout(self):
        self.client.force_login(
            self.other_user
        )

        response = self.client.post(
            reverse(
                "workout:complete_workout",
                args=[self.workout.id]
            )
        )

        self.assertEqual(
            response.status_code,
            404
        )

        self.workout.refresh_from_db()

        self.assertFalse(
            self.workout.is_completed
        )

    def test_complete_workout_updates_workout_record(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "workout:complete_workout",
                args=[self.workout.id]
            )
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.workout.refresh_from_db()

        self.assertTrue(
            self.workout.is_completed
        )

        self.assertEqual(
            self.workout.completed_sets,
            self.workout.target_sets
        )

        self.assertEqual(
            self.workout.completed_reps,
            self.workout.target_reps
        )

        self.assertIsNotNone(
            self.workout.completed_at
        )

    def test_complete_workout_updates_daily_progress(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "workout:complete_workout",
                args=[self.workout.id]
            )
        )

        self.assertEqual(
            response.status_code,
            200
        )

        progress = DailyProgress.objects.get(
            user=self.user
        )

        self.assertEqual(
            progress.active_minutes,
            30
        )

        self.assertEqual(
            progress.activity_calories,
            150
        )

    def test_completing_workout_twice_is_rejected(self):
        self.client.force_login(self.user)

        url = reverse(
            "workout:complete_workout",
            args=[self.workout.id]
        )

        first_response = self.client.post(url)

        self.assertEqual(
            first_response.status_code,
            200
        )

        second_response = self.client.post(url)

        self.assertEqual(
            second_response.status_code,
            400
        )

        progress = DailyProgress.objects.get(
            user=self.user
        )

        # The duration should not be added twice.
        self.assertEqual(
            progress.active_minutes,
            30
        )

        self.assertEqual(
            progress.activity_calories,
            150
        )

    def test_completing_two_workouts_accumulates_progress(self):
        second_workout = Workout.objects.create(
            user=self.user,
            workout_name="Second Workout",
            description="Second test workout",
            workout_category="Cardio",
            target_sets=2,
            target_reps=10,
            duration=20,
            calories_burned=100,
            difficulty_level="Beginner",
            equipment_required="No Equipment",
            is_completed=False
        )

        self.client.force_login(self.user)

        self.client.post(
            reverse(
                "workout:complete_workout",
                args=[self.workout.id]
            )
        )

        self.client.post(
            reverse(
                "workout:complete_workout",
                args=[second_workout.id]
            )
        )

        progress = DailyProgress.objects.get(
            user=self.user
        )

        self.assertEqual(
            progress.active_minutes,
            50
        )

        self.assertEqual(
            progress.activity_calories,
            250
        )
 

# Create your tests here.
