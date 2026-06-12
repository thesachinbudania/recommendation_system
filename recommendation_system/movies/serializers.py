from typing import Any

from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework import serializers
from .models import Movie

class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ["id", "title", "genres"]


class PreferenceDetailSerializer(serializers.Serializer):
    genre = serializers.CharField(max_length=100, required=False, allow_blank=True)
    director = serializers.CharField(max_length=100, allow_blank=True, required=False)
    actor = serializers.CharField(max_length=100, allow_blank=True, required=False)
    year = serializers.IntegerField(min_value=1900, max_value=2099, required=False, allow_null=True)

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        if all(value in [None, ""] for value in data.values()):
            raise serializers.ValidationError("At least one preference must be provided.")
        return data


class AddPreferenceSerializer(serializers.Serializer):
    new_preferences = PreferenceDetailSerializer()


class AddToWatchHistorySerializer(serializers.Serializer):
    id = serializers.IntegerField()

    def validate_id(self, value: int) -> int:
        """Check if movie with given id exists"""
        if not Movie.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid movie ID. No such movie exists.")
        return value


class PreferencesSerializer(serializers.Serializer):
    genre = serializers.ListField(child=serializers.CharField(), required=False)
    director = serializers.ListField(child=serializers.CharField(), required=False)
    actor = serializers.ListField(child=serializers.CharField(), required=False)
    year = serializers.ListField(child=serializers.CharField(), required=False)


class WatchHistorySerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    year = serializers.IntegerField()
    director = serializers.CharField(max_length=255)
    actor = serializers.CharField(max_length=255)


class GeneralFileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value: InMemoryUploadedFile) -> InMemoryUploadedFile:
        # validate file size (e.g., 30 MB Limit)
        if value.size > 30485760:
            raise serializers.ValidationError("The file size exceeds the limit of 30 MB")

        # validate the MIME type
        allowed_types = ["text/csv", "application/json"]
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("Unsupported file type.")

        return value



