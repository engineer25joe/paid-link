from datetime import datetime, timedelta, timezone

import cloudinary
import cloudinary.uploader
import cloudinary.utils

import cloudinary.uploader


MAX_FILE_SIZES = {
    "pdf": 50 * 1024 * 1024,
    "video": 500 * 1024 * 1024,
}


ALLOWED_CONTENT_TYPES = {
    "pdf": {
        "application/pdf",
    },
    "video": {
        "video/mp4",
        "video/webm",
        "video/quicktime",
    },
}


def upload_content_file(file, content_type):
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Unsupported content type.")

    max_size = MAX_FILE_SIZES[content_type]

    if file.size > max_size:
        max_size_mb = max_size // (1024 * 1024)

        raise ValueError(
            f"{content_type.upper()} files must not exceed "
            f"{max_size_mb} MB."
        )

    if file.content_type not in ALLOWED_CONTENT_TYPES[content_type]:
        raise ValueError(
            f"Invalid file type for {content_type}."
        )

    resource_type = (
        "video"
        if content_type == "video"
        else "raw"
    )

    result = cloudinary.uploader.upload(
        file,
        resource_type=resource_type,
        type="private",
        folder="paid_link/content",
    )

    return {
        "public_id": result["public_id"],
        "secure_url": result.get("secure_url"),
        "resource_type": result.get("resource_type"),
    }


def generate_private_content_url(content):
    if not content.cloudinary_public_id:
        raise ValueError("Content file is not available.")

    if content.content_type == "pdf":
        resource_type = "raw"
        file_format = "pdf"
    elif content.content_type == "video":
        resource_type = "video"
        file_format = "mp4"
    else:
        raise ValueError("Unsupported content type.")

    expires_at = int(
        (datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()
    )

    return cloudinary.utils.private_download_url(
        content.cloudinary_public_id,
        file_format,
        resource_type=resource_type,
        type="private",
        expires_at=expires_at,
        secure=True,
    )