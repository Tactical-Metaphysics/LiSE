from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser
from .models import Game
from .serializers import UserSerializer, GameSerializer


# Create your views here.
@csrf_exempt
def game_list(request):
	"""List all games, or create a new game"""
	if request.method == "GET":
		games = Game.objects.all()
		serializer = GameSerializer(games, many=True)
		return JsonResponse(serializer.data, safe=False)
	elif request.method == "POST":
		data = JSONParser().parse(request)
		serializer = GameSerializer(data=data)
		if serializer.is_valid():
			serializer.save()
			return JsonResponse(serializer.data, status=201)
		return JsonResponse(serializer.errors, status=400)


@csrf_exempt
def game_detail(request, pk):
	try:
		game = Game.objects.get(pk=pk)
	except Game.DoesNotExist:
		return HttpResponse(status=404)
	if request.method == "GET":
		serializer = GameSerializer(game)
		return JsonResponse(serializer.data)
	elif request.method == "PUT":
		data = JSONParser().parse(request)
		serializer = GameSerializer(game, data=data)
		if serializer.is_valid():
			serializer.save()
			return JsonResponse(serializer.data)
		return JsonResponse(serializer.errors, status=400)
	elif request.method == "DELETE":
		game.delete()
		return HttpResponse(status=204)


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
