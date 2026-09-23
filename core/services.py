import os

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class UserService:
    @staticmethod
    def create_user_with_role(validated_data):
        """Creates a user and automatically initializes the corresponding profile."""
        role = validated_data.get("role", "candidate")
        user = User.objects.create_user(
            email=validated_data["email"],
            name=validated_data["name"],
            phone=validated_data.get("phone", ""),
            role=role,
            password=validated_data["password"],
        )
        return user


class FileUploadService:
    ALLOWED_EXTENSIONS = ["pdf", "doc", "docx"]
    MAX_FILE_SIZE_MB = 5

    @classmethod
    def validate_and_replace_resume(cls, candidate_profile, file_obj):
        """Validates file size/format and safely replaces existing candidate resume."""
        if not file_obj:
            raise ValidationError("No file provided.")

        if file_obj.size > cls.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise ValidationError(f"File size exceeds the {cls.MAX_FILE_SIZE_MB}MB limit.")

        ext = file_obj.name.split(".")[-1].lower()
        if ext not in cls.ALLOWED_EXTENSIONS:
            raise ValidationError(
                f"Unsupported file format. Allowed: {', '.join(cls.ALLOWED_EXTENSIONS)}"
            )

        # Clean up existing file on disk if present
        if bool(candidate_profile.resume):
            try:
                if os.path.isfile(candidate_profile.resume.path):
                    os.remove(candidate_profile.resume.path)
            except (ValueError, FileNotFoundError):
                pass

        candidate_profile.resume = file_obj
        candidate_profile.save()
        return candidate_profile.resume.url
