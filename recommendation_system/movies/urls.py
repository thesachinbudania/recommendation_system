from django.urls import path

from movies.api import MovieDetailApiView, MovieListCreateApiView, UserPreferencesView, WatchHistoryView, \
    GeneralUploadView, MovieRecommendationsAPIView

app_name = 'movies'

urlpatterns = [
    path("movies/", MovieListCreateApiView.as_view(), name="movie-api"),
    path("movies/<int:pk>/", MovieDetailApiView.as_view(), name="movie-api-detail"),
    path("user/<int:user_id>/preferences/", UserPreferencesView.as_view(), name="user-preferences"),
    path("user/<int:user_id>/watch_history/", WatchHistoryView.as_view(), name="user-watch-history"),
    path("upload/", GeneralUploadView.as_view(), name="file-upload"),
    path("recommendations/", MovieRecommendationsAPIView.as_view(), name="movie_recommendations"),
]