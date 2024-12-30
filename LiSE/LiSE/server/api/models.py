from django.db import models


class Game(models.Model):
	created = models.DateTimeField(auto_now_add=True)
	prefix = models.FilePathField(allow_files=False, allow_folders=True)
	title = models.CharField(max_length=1000, blank=True, default="")

	class Meta:
		ordering = ["created"]
