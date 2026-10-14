from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch
from decimal import Decimal
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from .models import Content

# Create your tests here.


class UploadValidationTests(TestCase):
    def test_pdf_upload_rejects_mime_spoofed_non_pdf_before_provider_upload(self):
        from .services import upload_content_file
        upload = SimpleUploadedFile("notes.pdf", b"MZ executable", content_type="application/pdf")
        with patch("content.services.cloudinary.uploader.upload") as provider_upload:
            with self.assertRaisesMessage(ValueError, "PDF signature"):
                upload_content_file(upload, "pdf")
        provider_upload.assert_not_called()

    def test_video_upload_requires_supported_signature(self):
        from .services import upload_content_file
        upload = SimpleUploadedFile("movie.mp4", b"not a video", content_type="video/mp4")
        with patch("content.services.cloudinary.uploader.upload") as provider_upload:
            with self.assertRaisesMessage(ValueError, "video signature"):
                upload_content_file(upload, "video")
        provider_upload.assert_not_called()


class ContentOwnershipTests(TestCase):
    def test_creator_cannot_change_another_creators_content(self):
        owner = User.objects.create_user("owner", password="test")
        owner.profile.role = "creator"
        owner.profile.save()
        other = User.objects.create_user("other", password="test")
        other.profile.role = "creator"
        other.profile.save()
        item = Content.objects.create(creator=owner, title="Owner resource", description="Desc",
                                      content_type="pdf", price=Decimal("10"), is_published=False)
        client = APIClient()
        client.force_authenticate(other)
        response = client.patch(f"/api/content/{item.pk}/update/", {"title": "Stolen"}, format="json")
        self.assertEqual(response.status_code, 404)
        item.refresh_from_db()
        self.assertEqual(item.title, "Owner resource")
