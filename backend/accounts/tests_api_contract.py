from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken


class ApiAuthenticationContractTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_registration_login_refresh_and_authenticated_profile(self):
        registration = self.client.post("/api/accounts/register/", {
            "username": "contract_user", "email": "contract@example.test",
            "password": "safe-password-123", "phone_number": "254712345678",
        }, format="json")
        self.assertEqual(registration.status_code, 201)
        self.assertEqual(registration.data["message"], "Account created successfully.")
        self.assertEqual(registration.data["user"]["username"], "contract_user")
        self.assertEqual(registration.data["user"]["role"], "learner")
        self.assertIn("access", registration.data["tokens"])
        self.assertIn("refresh", registration.data["tokens"])

        login = self.client.post("/api/accounts/login/", {
            "username": "contract_user", "password": "safe-password-123",
        }, format="json")
        self.assertEqual(login.status_code, 200)
        self.assertIn("access", login.data)
        refreshed = self.client.post("/api/accounts/token/refresh/", {
            "refresh": login.data["refresh"],
        }, format="json")
        self.assertEqual(refreshed.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refreshed.data['access']}")
        profile = self.client.get("/api/accounts/profile/")
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.data["username"], "contract_user")

    def test_registration_rejects_password_shorter_than_eight_characters(self):
        response = self.client.post("/api/accounts/register/", {
            "username": "short_password_user", "email": "short@example.test",
            "password": "short", "phone_number": "254712345679",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)
        self.assertFalse(User.objects.filter(username="short_password_user").exists())

    def test_invalid_expired_and_missing_access_tokens_are_rejected(self):
        user = User.objects.create_user("token_test", password="safe-password-123")
        self.assertEqual(self.client.get("/api/accounts/profile/").status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer definitely-not-a-jwt")
        self.assertEqual(self.client.get("/api/accounts/profile/").status_code, 401)
        token = AccessToken.for_user(user)
        token["exp"] = int((timezone.now() - timedelta(minutes=1)).timestamp())
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.client.get("/api/accounts/profile/").status_code, 401)

    def test_role_restriction_and_mobile_json_authentication(self):
        learner = User.objects.create_user("contract_learner", password="safe-password-123")
        self.client.force_authenticate(learner)
        self.assertEqual(self.client.get("/api/accounts/creator/earnings/summary/").status_code, 403)
        # API requests work with Authorization headers and JSON without cookies or Origin.
        self.assertEqual(self.client.get("/api/accounts/profile/", HTTP_ACCEPT="application/json").status_code, 200)

    @override_settings(CORS_ALLOWED_ORIGINS=["https://frontend.example.test"])
    def test_cors_preflight_for_configured_frontend_origin(self):
        response = self.client.options(
            "/api/health/",
            HTTP_ORIGIN="https://frontend.example.test",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
        )
        self.assertEqual(response["Access-Control-Allow-Origin"], "https://frontend.example.test")


class HealthAndSafeErrorContractTests(TestCase):
    def test_health_has_a_secret_free_simple_response(self):
        response = APIClient().get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "ok"})

    @override_settings(DEBUG=False)
    def test_not_found_error_is_api_json_without_traceback_or_settings(self):
        response = APIClient().get("/api/content/999999/access/")
        self.assertEqual(response.status_code, 401)  # Authentication is required before resource lookup.
        user = User.objects.create_user("safe_error", password="safe-password-123")
        client = APIClient()
        client.force_authenticate(user)
        response = client.get("/api/content/999999/access/")
        self.assertEqual(response.status_code, 404)
        body = response.content.decode()
        self.assertNotIn("Traceback", body)
        self.assertNotIn("SECRET_KEY", body)
