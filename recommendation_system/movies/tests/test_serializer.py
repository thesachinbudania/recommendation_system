import pytest
from movies.models import Movie
from movies.serializers import MovieSerializer

@pytest.mark.django_db
def test_valid_movie_serializer():
    valid_data = {
        "title": "Inception",
        "genres": ["Action", "Sci-Fi"]
    }

    serializer = MovieSerializer(data=valid_data)
    assert serializer.is_valid()
    movie = serializer.save()

    assert Movie.objects.count() == 1
    created_movie = Movie.objects.get()
    assert created_movie.title == valid_data["title"]
    assert created_movie.genres == valid_data["genres"]


@pytest.mark.django_db
def test_invalid_movie_serializer():
    invalid_data = {
        "genres": ["Action", "Sci-Fi"]
    }

    serializer = MovieSerializer(data=invalid_data)

    assert not serializer.is_valid()

    assert "title" in serializer.errors


@pytest.mark.django_db
def test_serialize_movie_instance():
    movie = Movie.objects.create(title="Inception", genres=["Action", "Sci-Fi"])

    serializer = MovieSerializer(movie)

    assert serializer.data == {
        "id": movie.id,
        "title": movie.title,
        "genres": movie.genres
    }