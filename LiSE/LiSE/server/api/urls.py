from django.urls import path

from .views import *

urlpatterns = [
	path(
		"api/character",
		CharacterAPIView.as_view(),
		name="character_api_endpoint",
	)
]
