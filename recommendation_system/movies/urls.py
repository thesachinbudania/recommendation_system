from django.urls import path

from movies.api import MovieDetailApiView, MovieListCreateApiView

app_name = 'movies'

urlpatterns = [
    path("movies/", MovieListCreateApiView.as_view(), name="movie-api"),
    path("movies/<int:pk>/", MovieDetailApiView.as_view(), name="movie-api-detail"),
]