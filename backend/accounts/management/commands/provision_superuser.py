import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Create the explicitly configured initial Django superuser once."

    def handle(self, *args, **options):
        enabled = os.getenv("DJANGO_SUPERUSER_ENABLED", "false").strip().lower()
        if enabled not in {"1", "true", "yes", "on"}:
            self.stdout.write("Superuser provisioning is disabled.")
            return

        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "").strip()
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "")
        if not username or not email or not password:
            raise CommandError("Enabled superuser provisioning requires username, email, and password configuration.")
        if len(password) < 14:
            raise CommandError("The configured superuser password must be at least 14 characters.")

        User = get_user_model()
        with transaction.atomic():
            user = User.objects.select_for_update().filter(username=username).first()
            if user:
                if not user.is_superuser:
                    raise CommandError("The configured username belongs to a non-superuser account; no changes were made.")
                self.stdout.write("Configured superuser already exists; no changes made.")
                return
            if User.objects.filter(email__iexact=email).exists():
                raise CommandError("The configured email belongs to another account; no changes were made.")
            try:
                validate_password(password, user=User(username=username, email=email))
            except Exception as exc:
                raise CommandError("The configured password does not meet Django's password validation requirements.") from exc
            User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write("Configured superuser created.")
