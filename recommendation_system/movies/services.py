import csv
import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, Tuple, IO
import re
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from movies.models import UserMoviePreferences, Movie
from movies.serializers import PreferencesSerializer
import logging

logger = logging.getLogger(__name__)

def add_preference(user_id: int, new_preferences: Dict[str, Any]) -> None:
    """
        Adds new preferences or updates existing ones in the user's movie preferences,
        using defaultdict to avoid duplicate entries and handle lists
    :param user_id: ID of the user
    :param new_preferences: Dict containing new preferences to be added or updated
    """
    with transaction.atomic():
       user = get_object_or_404(get_user_model(), id=user_id)
       (
           user_preferences,
           created,
       ) = UserMoviePreferences.objects.select_for_update().get_or_create(
           user_id=user.id, defaults={"preferences": {}}
       )

    # Convert existing preferences to defaultdict
    current_preferences = defaultdict(list, user_preferences.preferences)
    for key, value in new_preferences.items():
        if value not in current_preferences[key]:
            current_preferences[key].append(value)

    # Convert defaultdict back to dict
    user_preferences.preferences = dict(current_preferences)
    user_preferences.save()

def add_watch_history(user_id: int, movie_id: int) -> None:
    """
    Adds a new movie to the user's watch history
    :param user_id: ID of the user
    :param movie_id: ID of the movie to be added
    """
    movie = get_object_or_404(Movie, id=movie_id)
    movie_info = {
        "title": movie.title,
        "year": movie.release_year,
        "director": movie.extra_data.get("directors", []),
        "genre": movie.genres
    }
    try:
        with transaction.atomic():
            user_preferences, created = UserMoviePreferences.objects.get_or_create(
                user_id=user_id, defaults={"watch_history": [movie_info]}
            )
    except IntegrityError:
        user_preferences = UserMoviePreferences.objects.get(user_id=user_id)
        created = False

    if not created:
        current_watch_history = user_preferences.watch_history
        current_watch_history.append(movie_info)
        user_preferences.watch_history = current_watch_history
        user_preferences.save()


def user_preferences(user_id: int) -> Any:
    user_preferences = get_object_or_404(UserMoviePreferences, user_id=user_id)
    serializer = PreferencesSerializer(user_preferences.preferences)
    return serializer.data


def user_watch_history(user_id: int) -> Any:
    user_preferences = get_object_or_404(UserMoviePreferences, user_id=user_id)
    return {"watch_history" : user_preferences.watch_history}


def parse_csv(file: IO[Any]) -> int:
    movies_processed = 0
    reader = csv.DictReader(file)
    for row in reader:
        extra_data = row.pop("extra_data")
        if extra_data:
            extra_data = extra_data.replace("'", '"')
            try:
                extra_data_dict = json.loads(extra_data)
            except json.decoder.JSONDecodeError:
                extra_data_dict = {}
        else:
            extra_data_dict = {}
        row["extra_data"] = extra_data_dict
        try:
            row["release_year"] = int(row["release_year"])
        except KeyError:
            pass
        row["title"] = clean_text(row["title"])
        row["genres"] = [clean_text(genre) for genre in row["genres"].split(',')]
        row["country"] = clean_text(row["country"])
        logger.info("Current movie: %s", row)
        create_or_update_movie(**row)
        movies_processed += 1
    return movies_processed


def parse_json(file: IO[Any]) -> int:
    movies_processed = 0
    data = json.load(file)
    for item in data:
        create_or_update_movie(**item)
        movies_processed += 1
    return movies_processed


class FileProcessor:
    def process(self, file_name: str, file_type: str) -> int | ValidationError:
        if default_storage.exists(file_name):
            with default_storage.open(file_name, "r") as file:
                if file_type == "text/csv":
                    movies_processed = parse_csv(file)
                elif file_type == "application/json":
                    movies_processed = parse_json(file)
                else:
                    raise ValidationError("Invalid file type")
            return movies_processed
        else:
            return ValidationError("File doesn't exists in storage.")


def create_or_update_movie(
        title: str,
        genres: list,
        country: str | None = None,
        extra_data: dict[Any, Any] | None = None,
        release_year: int | None = None
) -> Tuple[Movie, bool]:
   """
    Service function to create or update a movie instance.
   """
   try:
        # Ensure the release_year is within an acceptable range
        current_year = datetime.now().year
        if release_year is not None and (release_year < 1888 or release_year > current_year):
            raise ValidationError("The release year must be between 1888 and current year.")

        # Attempt to update an existing movie or create a new one
        movie, created = Movie.objects.update_or_create(
            title=title,
            defaults={
                "genres": genres,
                "country": country,
                "extra_data": extra_data,
                "release_year": release_year
            }
        )
        return movie, created
   except Exception as e:
       logger.info("Error while creating movie %s", e)
       raise ValidationError(f"Failed to create or update the movie {str(e)}")


def detect_q_string(text: str) -> list:
    """
    Detects strings that start with 'Q' followed by digits, useful for cleaning specific formats.
    :param text: string to find the pattern in
    :return:list of the found patterns
    """
    pattern = r'Q\d+'
    return re.findall(pattern, text)


def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""

    # Convert text to lowercase
    text = text.lower()

    # Remove any non-alphanumeric characters keeping words and digits
    text = re.sub(r"[^a-zA-Z0-9]", " ", text)

    # Tokenize the text into words
    words = word_tokenize(text)

    # Remove stopwords
    stop_words = set(stopwords.words("english"))
    words = [word for word in words if word not in stop_words]

    # Initialize lemmatizer and lemmatize the words
    lemmatizer = WordNetLemmatizer()
    words = [lemmatizer.lemmatize(word) for word in words]
    return ' '.join(words)