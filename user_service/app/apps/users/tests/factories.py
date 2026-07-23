import factory
from app.apps.users.models import User
from app.apps.profiles.models import Profile
from app.apps.authentication.models import AuthMethod
from django.contrib.auth.hashers import make_password

DEFAULT_PASSWORD = "StrongPass123!"

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    is_active = True
    is_email_verified = False
    is_phone_verified = False
    password = factory.LazyFunction(lambda: make_password(DEFAULT_PASSWORD))

class AuthMethodFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AuthMethod

    user = factory.SubFactory(UserFactory)
    provider = AuthMethod.EMAIL
    is_verified = True
    is_active = True

class ProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Profile

    user = factory.SubFactory(UserFactory)