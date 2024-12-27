from django.shortcuts import render
from rest_framework.views import APIView


# Create your views here.


class CharacterAPIView(APIView):
	def get_renderer_context(self):
		ret = super().get_renderer_context()
		# add the engine to ret
		return ret
