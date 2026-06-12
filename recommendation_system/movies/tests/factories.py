from factory.django import DjangoModelFactory, Password
from factory import Faker
from movies.models import Movie
from django.contrib.auth.models import User

class MovieFactory(DjangoModelFactory):
    class Meta:
        model = Movie

    title = Faker('sentence', nb_words=4)
    genres = Faker('pylist', nb_elements=3, variable_nb_elements=True, value_types=['str'])

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    password = Password('pw')