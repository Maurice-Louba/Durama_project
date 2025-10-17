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
                <table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#ffffff" style="max-width:600px; border-radius:8px; box-shadow:0 4px 12px rgba(0,0,0,0.08); overflow:hidden;">
                    <!-- En-tête -->
                    <tr>
                        <td bgcolor="#1e3d59" style="padding: 30px; text-align: center; border-bottom: 4px solid #f39c12;">
                            <h1 style="color: #ffffff; margin:0; font-size:28px; font-weight:700;">
                                Durama <span style="color: #f39c12;">BTP</span>
                            </h1>
                            <p style="color: #ecf0f1; margin:10px 0 0; font-size:16px; font-weight:300;">
                                Le meilleur du matériel BTP en un seul endroit
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Contenu principal -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <h2 style="color: #2c3e50; margin-top:0;">Bonjour <strong>{user.first_name or "cher client"}</strong>,</h2>
                            <p style="color: #34495e; line-height:1.6; font-size:16px;">
                                Merci de vous être inscrit sur <strong style="color: #f39c12;">Durama</strong>, 
                                votre marketplace dédiée à la vente de matériel et équipements BTP de qualité.
                            </p>
                            
                            <p style="color: #34495e; line-height:1.6; font-size:16px;">
                                Pour confirmer votre adresse e-mail et activer votre compte, veuillez utiliser le code OTP ci-dessous :
                            </p>
                            
                            <!-- Code OTP -->
                            <div style="text-align:center; margin:30px 0; padding:20px; background-color:#f9f9f9; border-radius:6px; border-left:4px solid #f39c12;">
                                <p style="color: #7f8c8d; margin:0 0 10px; font-size:14px;">Votre code de vérification :</p>
                                <span style="font-size:32px; font-weight:bold; color: #2c3e50; letter-spacing:4px; padding:12px 20px; background-color:#ecf0f1; border-radius:4px; display:inline-block;">
                                    {otp.otp_code}
                                </span>
                            </div>
                            
                            <p style="color: #e74c3c; font-size:14px; text-align:center;">
                                ⏳ Ce code expirera dans <strong>5 minutes</strong>
                            </p>
                            
                            <p style="color: #34495e; line-height:1.6; font-size:16px;">
                                Une fois votre compte activé, vous pourrez :
                            </p>
                            
                            <ul style="color: #34495e; line-height:1.8;">
                                <li>Accéder à un large choix de matériel BTP</li>
                                <li>Commander vos équipements en toute sécurité</li>
                                <li>Bénéficier d’offres et promotions exclusives</li>
                                <li>Gagner du temps grâce à une plateforme intuitive</li>
                            </ul>
                            
                            <div style="text-align:center; margin:30px 0;">
                                <a href="https://durama.com" style="background-color: #f39c12; color: white; padding: 14px 28px; text-decoration: none; border-radius:4px; font-weight:500; display:inline-block; font-size:16px;">
                                    Accéder à mon compte
                                </a>
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Pied de page -->
                    <tr>
                        <td bgcolor="#1e3d59" style="padding: 25px; text-align: center;">
                            <p style="color: #ecf0f1; margin:0; font-size:14px;">
                                &copy; 2025 Durama. Tous droits réservés.
                            </p>
                            <p style="color: #bdc3c7; margin:10px 0 0; font-size:12px;">
                                Si vous n'avez pas demandé ce code, ignorez simplement ce mail.
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
