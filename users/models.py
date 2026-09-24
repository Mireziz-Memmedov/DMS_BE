from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    position = models.CharField(
        max_length=150,
        blank=True
    )

    class Meta:
        db_table = 'user'

    def __str__(self):
        return self.username