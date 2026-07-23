import factory
from app.apps.authentication.models.auth_method import AuthMethod
from app.apps.users.tests.factories import UserFactory


class AuthMethodFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AuthMethod

    user = factory.SubFactory(UserFactory)
    provider = AuthMethod.EMAIL
    is_verified = True
    is_active = True