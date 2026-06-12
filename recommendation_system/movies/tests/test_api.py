import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.defaultfilters import title
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
import json

from movies.models import Movie
from movies.tests.factories import (
    MovieFactory,
    UserFactory
)

@pytest.mark.django_db
def test_create_movie(client):
    url = reverse("movies:movie-api")
    data = {"title": "A New Hope", "genres": ["Scri-Fi", "Adventure"]}

    response = client.post(
        url,
        data=data,
        content_type="application/json",
    )
    assert response.status_code == status.HTTP_201_CREATED, response.json()
    assert Movie.objects.filter(title="A New Hope").count() == 1

@pytest.mark.django_db
def test_retrieve_movie(client):
    movie = MovieFactory()
    url = reverse("movies:movie-api-detail", kwargs={"pk": movie.id})

    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "id": movie.id,
        "title": movie.title,
        "genres": movie.genres,
    }


@pytest.mark.django_db
def test_update_movie(client):
    movie = MovieFactory()
    new_title = "Updated Movie Title"
    url = reverse("movies:movie-api-detail", kwargs={"pk": movie.id})
    data = {"title": new_title}

    response = client.put(url, data=data, content_type="application/json")

    assert response.status_code == status.HTTP_200_OK, response.json()
    movie = Movie.objects.filter(id=movie.id).first()
    assert movie
    assert movie.title == new_title


@pytest.mark.django_db
def test_delete_movie(client):
    movie = MovieFactory()
    url = reverse("movies:movie-api-detail", kwargs={"pk": movie.id})

    response = client.delete(url)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Movie.objects.filter(id=movie.id).exists()


from django.test import override_settings

@pytest.mark.django_db
@override_settings(REST_FRAMEWORK={'PAGE_SIZE': 10})
def test_list_movies_with_pagination(client):
    movies = MovieFactory.create_batch(10)

    url = reverse("movies:movie-api")

    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert "count" in data
    assert "next" in data
    assert "previous" in data
    assert "results" in data

    assert data["count"] == 10

    assert data["next"] is None
    assert data["previous"] is None

    assert len(data["results"]) == 10

    returned_movie_ids = {movie["id"] for movie in data["results"]}
    expected_movie_ids = {movie.id for movie in movies}
    assert returned_movie_ids == expected_movie_ids

    for movie_data in data["results"]:
        assert set(movie_data.keys()) == {"id", "title", "genres"}

# test to check valid add new preferences route
@pytest.mark.django_db
@pytest.mark.parametrize(
    "new_preferences, expected_genre",
    [
        ({"genre": "sci-fi"}, "sci-fi"),
        ({"genre": "drama"}, "drama"),
        ({"genre": "action"}, "action"),
        ({"genre": "sci-fi", "actor": "Sigourney Weaver", "year": "1979"}, "sci-fi")
    ]
)
def test_add_and_retrieve_preferences_success(new_preferences, expected_genre):
    user = UserFactory()
    client = APIClient()
    preferences_url = reverse("movies:user-preferences", kwargs={"user_id": user.id})

    # Add new preferences
    response = client.post(preferences_url, {"new_preferences": new_preferences}, format="json")
    assert response.status_code in [200, 201]

    # Retrieve preferences to verify
    response = client.get(preferences_url)
    assert response.status_code == 200
    assert response.data["genre"] == [expected_genre]


# invalid add preferences
@pytest.mark.django_db
@pytest.mark.parametrize(
    "new_preferences",
    [
        ({}),
        ({"invalid_field": "value"})
    ]
)
def test_add_preferences_failure(new_preferences):
    user = UserFactory()
    client = APIClient()
    preferences_url = reverse("movies:user-preferences", kwargs={"user_id": user.id})

    # Attempt to add new preferences
    response = client.post(preferences_url, {"new_preferences": new_preferences}, format="json")
    assert response.status_code == 400, response.json()

# add and retrieve watch history
@pytest.mark.django_db
def test_add_and_retrieve_watch_history_with_movie_id():
    user = UserFactory()
    client = APIClient()
    watch_history_url = reverse("movies:user-watch-history", kwargs={"user_id": user.id})

    # Create movies instances using Movie Factory
    movie1 = MovieFactory(
        title="The Godfather",
        release_year = 1972,
        extra_data={"directors": ["Francis Ford Coppola"]},
        genres=["Crime", "Drama"]
    )
    movie2 = MovieFactory(
        title="Taxi Driver",
        release_year=1976,
        extra_data={"directors": ["Martin Scorsese"]},
        genres=["Crime", "Drama"]
    )

    # Add movies to watch history using their IDs
    for movie in [movie1, movie2]:
        response = client.post(watch_history_url, {"id": movie.id}, format="json")
        assert response.status_code == 201

    # Retrieve watch history and verify addition
    response = client.get(watch_history_url)
    assert response.status_code == 200
    retrieved_movie_ids = [item["title"] for item in response.data["watch_history"]]
    for movie_title in [movie1.title, movie2.title]:
        assert movie_title in retrieved_movie_ids


# Adding non-existent movie id should return 400
@pytest.mark.django_db
def test_add_invalid_movie_id_to_watch_history() -> None:
    user = UserFactory()
    client = APIClient()
    watch_history_url = reverse("movies:user-watch-history", kwargs={"user_id": user.id})

    invalid_movie_id = 99999
    response = client.post(watch_history_url, {"id": invalid_movie_id}, format="json")
    assert response.status_code == 400, "Expected a 400 Bad Request response for an invalid movie ID"


# valid file uploads
test_data = [(
    "file.csv",
    "text/csv",
    b"title,genres,extra_data\ntest,comedy,{\"directors\":[\"name\"]}\n",
    202
    ), #Expected to succeed for CSV
    (
       "file.json",
        "application/json",
        b'[{"title":"test", "genres": ["comedy"], "extra_data": {"directors": ["name"]}}]',
        202,
    ), # Expected to succeed for JSON
    (
       "file.txt",
        "text/plain",
        b"This is a test.",
        400
    ), # Unsupported file type, expecting failure
]

@pytest.mark.parametrize("file_name, content_type, file_content, expected_status", test_data)
@pytest.mark.django_db
def test_general_upload_view(client:APIClient, file_name: str, content_type: str, file_content: str, expected_status: int):
    # generate the URL dynamically using reverse
    url = reverse("movies:file-upload")

    # Create an in-memory uploaded file
    uploaded_file = SimpleUploadedFile(name=file_name, content=file_content, content_type=content_type)

    # Make a POST request to the GeneralUploadView endpoint
    response = client.post(url, {"file": uploaded_file}, format="multipart")
    print(response.data)
    assert response.status_code == expected_status


