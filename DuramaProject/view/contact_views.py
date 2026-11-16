import logging

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from ..serializer import MessageContactSerializer

logger = logging.getLogger(__name__)


class ContactThrottle(AnonRateThrottle):
    """Anti-spam : 5 messages par heure et par adresse IP."""
    scope = 'contact'
    rate = '5/hour'

    def get_rate(self):
        return self.rate


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@throttle_classes([ContactThrottle])
def envoyer_message_contact(request):
    """Formulaire de la page Contact : enregistre le message (visible dans l'admin) et prévient l'équipe."""
    serializer = MessageContactSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    user = request.user if request.user.is_authenticated else None
    message = serializer.save(user=user)

    destinataire = getattr(settings, 'EMAIL_HOST_USER', '') or getattr(settings, 'DEFAULT_FROM_EMAIL', '')
    if destinataire:
        try:
            send_mail(
                f"[Contact Durama] {message.sujet}",
                f"De : {message.nom or '—'} <{message.email}>\n"
                f"Téléphone : {message.telephone or '—'}\n\n{message.message}",
                settings.DEFAULT_FROM_EMAIL,
                [destinataire],
            )
        except Exception:
            # Le message est enregistré quoi qu'il arrive : l'équipe le retrouve dans l'admin
            logger.exception("Échec de la notification e-mail du message de contact %s", message.pk)

    return Response({'message': 'Message envoyé. Nous vous répondons au plus vite.'}, status=status.HTTP_201_CREATED)
