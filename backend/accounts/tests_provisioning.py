from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ProvisionSuperuserTests(TestCase):
    values = {
        "DJANGO_SUPERUSER_ENABLED": "true",
        "DJANGO_SUPERUSER_USERNAME": "initial-admin",
        "DJANGO_SUPERUSER_EMAIL": "initial-admin@example.test",
        "DJANGO_SUPERUSER_PASSWORD": "A-long-unique-password-2026!",
    }

    def invoke(self, values=None):
        environment = self.values if values is None else values
        with patch.dict("os.environ", environment, clear=True):
            call_command("provision_superuser", stdout=StringIO())

    def test_creates_initial_superuser_with_hashed_password(self):
        self.invoke()
        user = User.objects.get(username="initial-admin")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password(self.values["DJANGO_SUPERUSER_PASSWORD"]))

    def test_repeated_execution_keeps_password_unchanged(self):
        self.invoke()
        user = User.objects.get(username="initial-admin")
        old_hash = user.password
        self.invoke()
        user.refresh_from_db()
        self.assertEqual(user.password, old_hash)

    def test_disabled_or_missing_configuration_does_not_create_user(self):
        self.invoke({"DJANGO_SUPERUSER_ENABLED": "false"})
        with self.assertRaises(CommandError):
            self.invoke({"DJANGO_SUPERUSER_ENABLED": "true"})
        self.assertFalse(User.objects.exists())

    def test_username_conflict_never_elevates_regular_user(self):
        User.objects.create_user("initial-admin", password="ordinary-password")
        with self.assertRaises(CommandError):
            self.invoke()
        self.assertFalse(User.objects.get(username="initial-admin").is_superuser)

    def test_email_conflict_and_weak_password_fail_without_logging_secret(self):
        User.objects.create_user("other", email="initial-admin@example.test", password="ordinary-password")
        with self.assertRaises(CommandError):
            self.invoke()
        weak = {**self.values, "DJANGO_SUPERUSER_PASSWORD": "short"}
        with self.assertRaises(CommandError):
            self.invoke(weak)
        self.assertFalse(User.objects.filter(username="initial-admin").exists())
