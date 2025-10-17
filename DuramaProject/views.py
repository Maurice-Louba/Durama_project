from django.shortcuts import render
from django.shortcuts import render
from rest_framework import generics, permissions
from .models import User,EmailOTP
from .serializer import RegisterSerializer
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.exceptions import ObjectDoesNotExist
# Create your views here.



from django.core.mail import EmailMultiAlternatives

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()  # Par défaut, user.is_active = False

        # Générer OTP et l’associer à l’utilisateur
        otp = EmailOTP.objects.create(user=user)
        otp.generate_otp()

        # Sujet du mail
        subject = "Bienvenue sur Durama ! Confirmez votre adresse e-mail"

        # Version texte brut (fallback)
        text_content = f"""
Bonjour {user.first_name or 'cher client'},

Bienvenue sur Durama, la marketplace spécialisée dans le matériel BTP.

Votre code de vérification est : {otp.otp_code}

⏳ Ce code expirera dans 5 minutes.

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
                                Bonjour <strong style="color: #000000;">{user.first_name or "cher client"}</strong>,
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
                                ⏳ Code valable pendant <strong>5 minutes</strong>
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
            'no-reply@durama.com',  # expéditeur
            [user.email]            # destinataire
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        return Response({"message": "Utilisateur créé. Un OTP a été envoyé par email."}, status=status.HTTP_201_CREATED)



@api_view(['POST'])
def verify_otp(request):
    email = request.data.get('email')
    otp_code = request.data.get('otp')

    try:
        user = User.objects.get(email=email)
        otp_obj = EmailOTP.objects.get(user=user, otp_code=otp_code)
        
        if otp_obj.is_expired(): 
            return Response({'error': 'OTP expiré'}, status=400)

        # Activation de l'utilisateur
        user.is_active = True
        user.save()

        # Suppression de l'OTP utilisé
        otp_obj.delete()

        # Génération du token JWT
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)

        return Response({
            'message': 'Email vérifié avec succès',
            'access': access,
            'refresh': str(refresh),
        }, status=200)
    
    except ObjectDoesNotExist:
        return Response({'error': 'OTP invalide ou utilisateur non trouvé'}, status=400)
