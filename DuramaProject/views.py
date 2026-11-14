import logging

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.utils.html import escape
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import OTP_VALIDITE_MINUTES, EmailOTP, Panier, User
from .serializer import RegisterSerializer

logger = logging.getLogger(__name__)

# Nombre d'essais OTP faux autorisés avant d'invalider le code
OTP_ESSAIS_MAX = 5


class OTPThrottle(AnonRateThrottle):
    """Limite les tentatives par adresse IP (anti force brute sur les codes à 6 chiffres)."""
    scope = 'otp'
    rate = '10/min'

    def get_rate(self):
        return self.rate


class InscriptionThrottle(AnonRateThrottle):
    scope = 'inscription'
    rate = '20/hour'

    def get_rate(self):
        return self.rate


class ConnexionView(TokenObtainPairView):
    """Connexion (email + mot de passe -> JWT), limitée en débit contre le vol de mot de passe."""
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'connexion'


def envoyer_email_otp(user, otp):
    # Sujet du mail
    subject = "Bienvenue sur Durama ! Confirmez votre adresse e-mail"

    # Version texte brut (fallback)
    text_content = f"""
Bonjour {user.first_name or 'cher client'},

Bienvenue sur Durama, la marketplace spécialisée dans le matériel BTP.

Votre code de vérification est : {otp.otp_code}

⏳ Ce code expirera dans {OTP_VALIDITE_MINUTES} minutes.

Une fois votre compte activé, vous pourrez :
- Accéder à un large choix de matériel BTP
- Commander vos équipements en toute sécurité
- Profiter d’offres et promotions exclusives
- Gagner du temps grâce à une plateforme intuitive

Cordialement,
L’équipe Durama
"""

    # Version HTML avec design Durama
    html_content = f"""
<html>
<head>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
</style>
</head>
<body style="font-family: 'Roboto', Arial, sans-serif; background-color:#f8f9fa; padding:0; margin:0;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f8f9fa">
    <tr>
        <td align="center" style="padding: 40px 0;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#ffffff" style="max-width:600px; border-radius:12px; box-shadow:0 8px 24px rgba(0,0,0,0.08); overflow:hidden; border: 1px solid #e5e7eb;">
                <!-- En-tête -->
                <tr>
                    <td bgcolor="#000000" style="padding: 35px; text-align: center; border-bottom: 1px solid #e5e7eb;">
                        <h1 style="color: #ffffff; margin:0; font-size:32px; font-weight:700; letter-spacing: -0.5px;">
                            DURAMA
                        </h1>
                        <p style="color: #9ca3af; margin:12px 0 0; font-size:16px; font-weight:400;">
                            Votre marketplace BTP premium
                        </p>
                    </td>
                </tr>
                
                <!-- Contenu principal -->
                <tr>
                    <td style="padding: 45px 35px;">
                        <h2 style="color: #111827; margin-top:0; font-size:24px; font-weight:600; margin-bottom: 8px;">
                            Bonjour <strong style="color: #000000;">{escape(user.first_name or "cher client")}</strong>,
                        </h2>
                        
                        <p style="color: #374151; line-height:1.6; font-size:16px; margin-bottom: 20px;">
                            Bienvenue sur <strong style="color: #000000;">Durama</strong>, la plateforme d'excellence 
                            dédiée aux professionnels du BTP.
                        </p>
                        
                        <p style="color: #374151; line-height:1.6; font-size:16px; margin-bottom: 30px;">
                            Pour finaliser votre inscription et accéder à l'ensemble de nos services, 
                            veuillez utiliser le code de vérification ci-dessous :
                        </p>
                        
                        <!-- Code OTP -->
                        <div style="text-align:center; margin:35px 0; padding:25px; background-color:#f9fafb; border-radius:8px; border: 1px solid #e5e7eb;">
                            <p style="color: #6b7280; margin:0 0 12px; font-size:14px; font-weight:500;">VOTRE CODE DE VÉRIFICATION</p>
                            <span style="font-size:36px; font-weight:700; color: #000000; letter-spacing:6px; padding:16px 24px; background-color:#ffffff; border-radius:6px; display:inline-block; border: 2px solid #000000;">
                                {otp.otp_code}
                            </span>
                        </div>
                        
                        <p style="color: #dc2626; font-size:14px; text-align:center; font-weight:500; margin: 20px 0 30px;">
                            ⏳ Code valable pendant <strong>{OTP_VALIDITE_MINUTES} minutes</strong>
                        </p>
                        
                        <p style="color: #374151; line-height:1.6; font-size:16px; margin-bottom: 20px;">
                            Une fois votre compte activé, vous bénéficierez de :
                        </p>
                        
                        <ul style="color: #374151; line-height:1.7; margin: 0 0 30px 0; padding-left: 20px;">
                            <li style="margin-bottom: 8px;">Accès à notre catalogue premium de matériel BTP</li>
                            <li style="margin-bottom: 8px;">Commandes sécurisées et suivies en temps réel</li>
                            <li style="margin-bottom: 8px;">Offres exclusives réservées aux professionnels</li>
                            <li style="margin-bottom: 8px;">Interface optimisée pour une gestion simplifiée</li>
                        </ul>
                        
                        <div style="text-align:center; margin:35px 0 25px;">
                            <a href="https://durama.com" style="background-color: #000000; color: #ffffff; padding: 16px 32px; text-decoration: none; border-radius:8px; font-weight:600; display:inline-block; font-size:16px; border: 1px solid #000000; transition: all 0.3s ease;">
                                Accéder à la plateforme
                            </a>
                        </div>
                    </td>
                </tr>
                
                <!-- Pied de page -->
                <tr>
                    <td bgcolor="#f9fafb" style="padding: 25px; text-align: center; border-top: 1px solid #e5e7eb;">
                        <p style="color: #6b7280; margin:0 0 8px; font-size:14px;">
                            &copy; 2025 Durama. Tous droits réservés.
                        </p>
                        <p style="color: #9ca3af; margin:0; font-size:12px; line-height: 1.5;">
                            Si vous n'êtes pas à l'origine de cette demande,<br>
                            veuillez ignorer cet email.
                        </p>
                    </td>
                </tr>
            </table>
        </td>
    </tr>
</table>
</body>
</html>
"""

    # Envoi du mail HTML + texte brut
    email = EmailMultiAlternatives(
        subject,
        text_content,
        getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'no-reply@durama.com',  # expéditeur
        [user.email]            # destinataire
    )
    email.attach_alternative(html_content, "text/html")
    email.send()


def nouvel_otp(user):
    """Supprime les anciens codes de l'utilisateur et en crée un nouveau."""
    EmailOTP.objects.filter(user=user).delete()
    cache.delete(f"otp_essais:{user.pk}")
    otp = EmailOTP(user=user)
    otp.generate_otp()
    return otp


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [InscriptionThrottle]

    def perform_create(self, serializer):
        # Si l'envoi du mail échoue, le compte n'est pas créé (sinon l'email serait "déjà pris"
        # alors que l'utilisateur n'a jamais reçu de code)
        with transaction.atomic():
            user = serializer.save()  # user.is_active = False
            otp = nouvel_otp(user)
            envoyer_email_otp(user, otp)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@throttle_classes([OTPThrottle])
def verify_otp(request):
    email = (request.data.get('email') or '').strip()
    otp_code = str(request.data.get('otp') or '').strip()

    user = User.objects.filter(email__iexact=email).first()
    otp_obj = EmailOTP.objects.filter(user=user).order_by('-created_at').first() if user else None
    if otp_obj is None:
        return Response({'error': 'OTP invalide ou utilisateur non trouvé'}, status=400)

    if otp_obj.is_expired():
        otp_obj.delete()
        return Response({'error': 'OTP expiré'}, status=400)

    if otp_obj.otp_code != otp_code:
        cle = f"otp_essais:{user.pk}"
        essais = cache.get(cle, 0) + 1
        cache.set(cle, essais, timeout=OTP_VALIDITE_MINUTES * 60)
        if essais >= OTP_ESSAIS_MAX:
            otp_obj.delete()
            cache.delete(cle)
            return Response({'error': 'Trop de tentatives, demandez un nouveau code'}, status=400)
        return Response({'error': 'OTP invalide ou utilisateur non trouvé'}, status=400)

    with transaction.atomic():
        # Activation de l'utilisateur
        user.is_active = True
        user.is_confirmed = True
        user.save(update_fields=['is_active', 'is_confirmed'])

        # Création automatique du panier
        Panier.panier_actif(user)

        # Suppression de l'OTP utilisé
        EmailOTP.objects.filter(user=user).delete()
    cache.delete(f"otp_essais:{user.pk}")

    # Génération du token JWT
    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)

    return Response({
        'message': 'Email vérifié avec succès',
        'access': access,
        'refresh': str(refresh),
    }, status=200)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@throttle_classes([OTPThrottle])
def renvoyer_otp(request):
    """Renvoie un nouveau code à un compte pas encore activé."""
    email = (request.data.get('email') or '').strip()
    user = User.objects.filter(email__iexact=email, is_active=False).first()
    if user is not None:
        otp = nouvel_otp(user)
        try:
            envoyer_email_otp(user, otp)
        except Exception:
            logger.exception("Échec d'envoi de l'OTP à %s", user.email)
            return Response({'error': "Impossible d'envoyer l'email, réessayez plus tard"}, status=503)
    # Même réponse que le compte existe ou non : on ne révèle pas quels emails sont inscrits
    return Response({'message': 'Si un compte non activé existe pour cet email, un nouveau code a été envoyé.'})
