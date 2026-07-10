from django.conf import settings
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def send_sms(*, to: str, body: str) -> str:
    
    message = _client.messages.create(
        to=to,
        from_=settings.TWILIO_PHONE_NUMBER,
        body=body,
    )
    return message.sid