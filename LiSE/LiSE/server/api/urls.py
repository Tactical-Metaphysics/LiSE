from django.urls import path

from . import views

urlpatterns = [
	path("games/", views.game_list),
	path("games/<int:pk>/", views.game_detail),
	# path(
	# 	"api/character",
	# 	views.CharacterAPIView.as_view(),
	# 	name="character_api_endpoint",
	# ),
	path("users/", views.UserList.as_view()),
	path("users/<int:pk>/", views.UserDetail.as_view()),
]
