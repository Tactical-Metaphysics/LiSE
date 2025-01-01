from django.contrib.auth.models import User

from rest_framework import generics, status, mixins
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser
from .models import Game
from .serializers import UserSerializer, GameSerializer


# Create your views here.
class GameList(
	mixins.ListModelMixin, mixins.CreateModelMixin, generics.GenericAPIView
):
	"""List all games, or create a new game"""

	queryset = Game.objects.all()
	serializer_class = GameSerializer

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


class GameDetail(
	mixins.RetrieveModelMixin,
	mixins.UpdateModelMixin,
	mixins.DestroyModelMixin,
	generics.GenericAPIView,
):
	queryset = Game.objects.all()
	serializer_class = GameSerializer

	def get(self, request, pk, format=None):
		return self.retrieve(request, pk, format)

	def put(self, request, pk, format=None):
		return self.update(request, pk, format)

	def delete(self, request, pk, format=None):
		return self.destroy(request, pk, format)


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
