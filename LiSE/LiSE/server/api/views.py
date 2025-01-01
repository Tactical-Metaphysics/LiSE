from django.contrib.auth.models import User

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser
from .models import Game
from .serializers import UserSerializer, GameSerializer


# Create your views here.
class GameList(APIView):
	"""List all games, or create a new game"""

	def get(self, request, format=None):
		games = Game.objects.all()
		serializer = GameSerializer(games, many=True)
		return Response(serializer.data)

	def post(self, request, format=None):
		data = JSONParser().parse(request)
		serializer = GameSerializer(data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GameDetail(APIView):
	def get_object(self, pk):
		try:
			return Game.objects.get(pk=pk)
		except Game.DoesNotExist:
			return Response(status=status.HTTP_404_NOT_FOUND)

	def get(self, request, pk, format=None):
		game = self.get_object(pk)
		serializer = GameSerializer(game)
		return Response(serializer.data)

	def put(self, request, pk, format=None):
		game = self.get_object(pk)
		data = JSONParser().parse(request)
		serializer = GameSerializer(game, data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	def delete(self, request, pk, format=None):
		game = self.get_object(pk)
		game.delete()
		return Response(status=status.HTTP_204_NO_CONTENT)


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
