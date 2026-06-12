from django.urls import path
from rest_framework_simplejwt.views import (TokenObtainPairView, TokenRefreshView)
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('token/', obtain_auth_token, name="api_token_auth"),
    path('jwt_token/', TokenObtainPairView.as_view(), name='jwt_token'),
    path('jwt_token/refresh/', TokenRefreshView.as_view(), name='jwt_refresh'),
]