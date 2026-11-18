import json

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User


class UsersAuthTests(TestCase):

    def setUp(self):
        self.username = "testuser"
        self.password = "StrongPass123!"

        self.user = User.objects.create_user(
            username=self.username,
            email="test@example.com",
            password=self.password
        )

    def test_login_page_loads(self):
        response = self.client.get(reverse("users:login"))
        self.assertEqual(response.status_code, 200)

    def test_api_login_success(self):
        response = self.client.post(
            reverse("users:api_login"),
            data=json.dumps({
                "username": self.username,
                "password": self.password
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue("_auth_user_id" in self.client.session)

    def test_api_login_invalid_password(self):
        response = self.client.post(
            reverse("users:api_login"),
            data=json.dumps({
                "username": self.username,
                "password": "WrongPassword123"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_api_register_success(self):
        response = self.client.post(
            reverse("users:api_register"),
            data=json.dumps({
                "username": "newtestuser",
                "email": "new@example.com",
                "password1": "AnotherStrong123!",
                "password2": "AnotherStrong123!"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)

        self.assertTrue(
            User.objects.filter(username="newtestuser").exists()
        )

    def test_api_register_duplicate_username(self):
        response = self.client.post(
            reverse("users:api_register"),
            data=json.dumps({
                "username": self.username,
                "email": "duplicate@example.com",
                "password1": "AnotherStrong123!",
                "password2": "AnotherStrong123!"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

    def test_api_logout_success(self):
        self.client.login(
            username=self.username,
            password=self.password
        )

        response = self.client.post(
            reverse("users:api_logout")
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_requires_login(self):
        response = self.client.get(
            reverse("users:profile")
        )

        self.assertEqual(response.status_code, 302)

    def test_logged_in_user_can_access_profile(self):
        self.client.login(
            username=self.username,
            password=self.password
        )

        response = self.client.get(
            reverse("users:profile")
        )

        self.assertEqual(response.status_code, 200)
