import os.path
from typing import Any, Optional
import uuid
from django.core.files.base import ContentFile
from jmespath import ast
from rest_framework import generics, status
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Movie, UserMoviePreferences
from .serializers import MovieSerializer, AddPreferenceSerializer, AddToWatchHistorySerializer, \
    GeneralFileUploadSerializer, WatchHistorySerializer, PreferencesSerializer
from .services import add_preference, user_preferences, user_watch_history, add_watch_history
from contextlib import contextmanager
from django.core.files.storage import default_storage
from .tasks import process_file
from api_auth.permissions import CustomDjangoModelPermissions
from recommendations.services import UserPreferences, Item, get_recommendations
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
import requests

@extend_schema(
    summary="Retrieve all movies",
    description="Returns a paginated list of movies available in the system. Use filters and pagination parameter"
                "for larger datasets",
    responses={
        200: MovieSerializer(many=True)
    },
    parameters=[
        OpenApiParameter("page", int, description="Page number for pagination"),
        OpenApiParameter("size", int, description="Page size for pagination"),
    ],
    methods=["GET"],
)
@extend_schema(
    summary="Create a new movie",
    description="Adds a new movie to the system. Requires authentication and proper permission.",
    request=MovieSerializer,
    responses={
        201: MovieSerializer,
        400: OpenApiResponse(description="Bad Request. Validation error."),
        403: OpenApiResponse(description="Forbidden. Insufficient permissions.")
    },
    methods=['POST'],
)
@permission_classes([IsAuthenticated, CustomDjangoModelPermissions])
class MovieListCreateApiView(generics.ListCreateAPIView):
    queryset = Movie.objects.all().order_by("-id")
    serializer_class = MovieSerializer


@extend_schema(
    summary="Get a movie by id",
    description="Returns a particular movie details given the movie id.",
    responses={
        200: MovieSerializer
    },
    parameters=[
        OpenApiParameter("id", int, description="Id of the movie to retrieve"),
    ],
    methods=['GET']
)
@extend_schema(
    summary="Change a movie by id",
    description="Change all the data for an existing movie by it's id. Use to change the entire entry of a movie"
                "or replace a movie with another movie.",
    responses={
        200: MovieSerializer,
        400: OpenApiResponse(description="Bad Response. Validation error."),
        403: OpenApiResponse(description="Insufficient permissions."),
        404: OpenApiResponse(description="Movie not found.")
    },
    parameters=[
        OpenApiParameter("id", int, description="Id of the movie to change"),
    ],
    methods=['PUT'],
)
@extend_schema(
    summary="Update a movie by it's id",
    description="Update the data for an existing movie by it's id. Can update just parts of the movie without replacing"
                "the entire movie.",
    responses={
        200: MovieSerializer,
        400: OpenApiResponse(description="Bad Response. Validation error."),
        403: OpenApiResponse(description="Insufficient permissions."),
        404: OpenApiResponse(description="Movie not found."),
    },
    parameters=[
        OpenApiParameter("id", int, description="Id of the movie to update"),
    ],
    methods=['PATCH'],
)
@extend_schema(
    summary="Delete a movie by it's id",
    description="Delete an existing movie from the system. Requires id of the movie to be passed in the params.",
    responses={
        200: MovieSerializer,
        400: OpenApiResponse(description="Bad Response. Validation error."),
        403: OpenApiResponse(description="Insufficient permissions."),
        404: OpenApiResponse(description="Movie not found."),
    },
    parameters=[
        OpenApiParameter("id", int, description="Id of the movie to update"),
    ],
    methods=['DELETE'],
)
class MovieDetailApiView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer


@extend_schema(
    summary="Add new preferences for the user",
    description="Takes in the new preference details such as director, genre etc. and adds them to the users preferences"
                "in the system. Helpful in finding relavant recommendations.",
    request=AddPreferenceSerializer,
    responses={
        200: OpenApiResponse(description="Successfully added new preferences."),
    },
    methods=['POST'],
)
@extend_schema(
    summary="Fetches user's preferences",
    description="Given a user id in the user_id field fetches the preferences for the user set in the system.",
    responses={
        200: PreferencesSerializer,
    },
    methods=["GET"],
)
@permission_classes([IsAuthenticated,])
class UserPreferencesView(APIView):
    """
        View or add user preferences
    """
    def post(self, request: Request, user_id: int) -> Response:
        serializer = AddPreferenceSerializer(data=request.data)
        if serializer.is_valid():
            add_preference(user_id, serializer.validated_data["new_preferences"])
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request: Request, user_id: int) -> Response:
        data = user_preferences(user_id)
        return Response(data)


@extend_schema(
    summary="Add watch history for a user",
    description="Adds the provided watch history in the request body to the watch history of the user in the system.",
    request=AddToWatchHistorySerializer,
    responses={
        201: OpenApiResponse(description="Movie added to current user's watch history."),
        404: OpenApiResponse(description="Movie not found."),
    },
    methods=["POST"],
)
@extend_schema(
    summary="Fetch watch history",
    description="Returns the watch history in the system for the user with the given user id.",
    responses={
        200: WatchHistorySerializer(many=True),
        404: OpenApiResponse(description="User not found.")
    },
    methods=["GET"],
)
@permission_classes([IsAuthenticated,])
class WatchHistoryView(APIView):
    """
        View or add user watch history
    """
    def get(self, request: Request, user_id: int) -> Response:
        data = user_watch_history(user_id)
        return Response(data)

    def post(self, request: Request, user_id: int) -> Response:
        serializer = AddToWatchHistorySerializer(data=request.data)
        if serializer.is_valid():
            add_watch_history(
                user_id,
                serializer.validated_data["id"]
            )
            return Response(
                {"message": "Movie added to watch history."},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@contextmanager
def temporary_file(uploaded_file):
    file_name = default_storage.save(uploaded_file.name, uploaded_file)
    try:
        file_path = default_storage.path(file_name)
        yield file_path
    finally:
        default_storage.delete(file_name)

@extend_schema(
    summary="Upload a CSV or JSON file for adding new movies to the system.",
    description="Allows the user to upload properly formatted csv or json files and adds the movies and related data"
                "to the system. Supports background task processing.",
    request=GeneralFileUploadSerializer,
    responses={
        202: OpenApiResponse(
            description="File uploaded successfully. Job enqueued for processing.",
            examples={"application/json": {"message": "Job enqueued for processing."}}
        ),
        400: OpenApiResponse(
            description="Bad Request. Validation error or unsupported file.",
        )
    },
    methods=["POST"],
)
@permission_classes([IsAdminUser,])
class GeneralUploadView(APIView):
    def post(self, request, *args: Any, **kwargs: Any) -> Response:
        serializer = GeneralFileUploadSerializer(data=request.data)
        if serializer.is_valid():
            uploaded_file = serializer.validated_data["file"]
            file_type = uploaded_file.content_type

            file_extension = os.path.splitext(uploaded_file.name)[1]

            unique_file_name = f"{uuid.uuid4()}{file_extension}"
            file_name = default_storage.save(unique_file_name, ContentFile(uploaded_file.read()))
            process_file.delay(file_name, file_type)
            return Response(
            {
                    "message": f"Job enqueued for processing",
                },
                status=status.HTTP_202_ACCEPTED,
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    summary="Recommends movies to the user",
    description="Takes the users current preferences into account and suggest new movies to the user. Uses cosine"
                "similarity for finding new movies. To save computational resources, the functions calculating the"
                "preferences and recommendations have been hosted as AWS Lambda functions",
    parameters=[
        OpenApiParameter("user_id", int, description="Id of the user to recommend movies to.")
    ]
)
class MovieRecommendationsAPIView(APIView):
    """
        The code and functions in this api have not all been used directly but are rather hosted on AWS Lambda to use
        computational resources more efficiently.
    """
    def get(self, request):
        user_id = request.query_params.get("user_id")

        if not user_id:
            return self._response_error(
                detail="user_id query parameter is required.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user_preferences = self._get_user_preferences(user_id)
        if not user_preferences:
            return self._response_error(
                detail="User preferences not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        response = requests.get(f'{os.getenv('AWS_LAMBDA_URL')}?user_id={user_id}')
        response_data = self._format_response(response.json())
        return Response(response_data, status=status.HTTP_200_OK)

    def _get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """
            Retrieves user preferences from the database and converts them into the UserPreferences Pydantic model.
        """
        try:
            # Fetch user preferences from the database
            user_prefs = UserMoviePreferences.objects.get(user_id=user_id)

            # Extracting the relevant preferences
            genre = user_prefs.preferences.get("genre", [])
            director = user_prefs.preferences.get("director", [])
            actor = user_prefs.preferences.get("actor", [])
            year_range = user_prefs.preferences.get("year", [])

            # Handle year range if it's provided (expecting a list)
            year_range_start, year_range_end = (
            (year_range[0], year_range[-1]) if len(year_range) >= 2 else (None, None)
            )

            # Build the preferences dictionary
            preferences_dict = {
                "genre": genre,
                "director": director,
                "actor": actor,
                "year_range_start": year_range_start,
                "year_range_end": year_range_end
            }

            # Instantiate UserPreferences with the preferences dictionary
            return UserPreferences(
                preferences=preferences_dict,
                watch_history=[],
            )
        except UserMoviePreferences.DoesNotExist:
            return None

    def _get_recommended_items(self, user_preferences: UserPreferences) -> list[Item]:
        """
            Generates a list of recommended items (in this case, movies) based on user preferences.
        """
        movies = Movie.objects.all()
        items = [
            Item(
                id=movie.id,
                attributes={
                    "name": movie.title,
                    "genre": movie.genres,
                    "director": ast.literal(movie.extra_data).get("directors", ""),
                    "year": movie.release_year,
                }
            )
            for movie in movies
        ]

        return get_recommendations(user_preferences=user_preferences, items=items)

    def _format_response(self, recommended_items: list[Any]) -> list[dict]:
        """
        Formats the recommended items into a response-friendly structure.

        :param recommended_items: A list of Item objects representing recommended content.
        :return: A list of dictionaries with content ID and name.
        """
        return [
            {"id": item['id'], "title": item['title']}
            for item in recommended_items
        ]

    def _response_error(self, detail: str, status_code: int) -> Response:
        """
        Constructs an error response.

        :param detail: The error message to include in the response.
        :param status_code: The HTTP status code for the response.
        :return: A Response object with the error message and status code.
        """
        return Response({"detail": detail}, status=status_code)