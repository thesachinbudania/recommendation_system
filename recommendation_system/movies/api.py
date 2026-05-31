from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from .models import Movie
from .serializers import MovieSerializer

class MovieListCreateApiView(generics.ListCreateAPIView):
    queryset = Movie.objects.all().order_by("-id")
    serializer_class = MovieSerializer

class MovieDetailApiView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer