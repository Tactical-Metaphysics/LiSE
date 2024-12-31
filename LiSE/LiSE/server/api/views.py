from django.contrib.auth.models import User
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser
from rest_framework.decorators import api_view
from .models import Game
from .serializers import UserSerializer, GameSerializer


# Create your views here.
@api_view(["GET", "POST"])
def game_list(request):
	"""List all games, or create a new game"""
	if request.method == "GET":
		games = Game.objects.all()
		serializer = GameSerializer(games, many=True)
		return Response(serializer.data)
	elif request.method == "POST":
		data = JSONParser().parse(request)
		serializer = GameSerializer(data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "DELETE"])
def game_detail(request, pk):
	try:
		game = Game.objects.get(pk=pk)
	except Game.DoesNotExist:
		return Response(status=status.HTTP_404_NOT_FOUND)
	if request.method == "GET":
		serializer = GameSerializer(game)
		return Response(serializer.data)
	elif request.method == "PUT":
		data = JSONParser().parse(request)
		serializer = GameSerializer(game, data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	elif request.method == "DELETE":
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
