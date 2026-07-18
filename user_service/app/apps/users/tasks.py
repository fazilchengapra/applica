from celery import shared_task
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def revoke_all_tokens_task(self, user_id):
    try:
        tokens = OutstandingToken.objects.filter(user_id=user_id)
        for token in tokens:
            BlacklistedToken.objects.get_or_create(token=token)
    except Exception as exc:
        raise self.retry(exc=exc)