from django.db import models


class ChannelChoice(models.TextChoices):

    EMAIL = ("EMAIL", "Email Channel")

    SMS = ("SMS", "SMS Channel")
