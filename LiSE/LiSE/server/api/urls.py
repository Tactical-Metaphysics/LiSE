from django.urls import path

from .views import *

urlpatterns = [path('api/hello', HellowAPIView.as_view(), name='hello_api_endpoint')]