from django.contrib.auth.models import User

from rest_framework import generics
from rest_framework.views import APIView
from .models import Game
from .serializers import UserSerializer, GameSerializer


# Create your views here.
class GameList(generics.ListCreateAPIView):
	"""List all games, or create a new game"""

	queryset = Game.objects.all()
	serializer_class = GameSerializer


class GameDetail(generics.RetrieveUpdateDestroyAPIView):
	queryset = Game.objects.all()
	serializer_class = GameSerializer


class CharacterAPIView(APIView):
	def get_renderer_context(self):
		ret = super().get_renderer_context()
		# add the engine to ret
		return ret


class UserList(generics.ListAPIView):
	queryset = User.objects.all()
	serializer_class = UserSerializer


class UserDetail(generics.RetrieveAPIView):
	queryset = User.objects.all()
	serializer_class = UserSerializer
