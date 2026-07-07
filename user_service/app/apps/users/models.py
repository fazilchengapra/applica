from django.db import models

# User model
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager

# phone number filed package
from phonenumber_field.modelfields import PhoneNumberField

# manager for user model
from .manager import UserManager


class User(AbstractUser):
    # Remove the inherited field that only used inside the profile model
    username = None  # remove the inherited username field entirely
    first_name =None  # remove the inherited first_name field entirely
    last_name = None  # remove the inherited last_name field entirely

    email = models.EmailField(max_length=254, unique=True)

    # used a phonenumber_field package for truest phone number validation and formatting
    phone_number = PhoneNumberField(unique=True, null=True, blank=True)

    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)

    # Add a field to track when the user was deactivated
    deactivated_at = models.DateTimeField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    # custom user manager because we are using email as the unique identifier instead of username
    objects = UserManager()

    # Set the email field as the unique identifier for authentication instead of username
    USERNAME_FIELD = 'email'

    # user need to provide phone number when creating a account
    REQUIRED_FIELDS = []

    # String representation of the user model
    def __str__(self):
        return self.email
    
    # checking the user email and phone number is verified or not it's a field that return Boolean
    @property
    def is_fully_verified(self):
        return self.is_email_verified and self.is_phone_verified