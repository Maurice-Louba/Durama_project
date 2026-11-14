from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Addresse
from ..serializer import AdresseSerialized

NB_MAX_ADRESSES = 20


#  Liste toutes les adresses de l'utilisateur connecté
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def liste_adresses(request):
    adresses = Addresse.objects.filter(user=request.user).order_by('-is_default', '-created_at')
    serializer = AdresseSerialized(adresses, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# Créer une nouvelle adresse
@swagger_auto_schema(
    method='post',
    request_body=AdresseSerialized,
    responses={
        201: AdresseSerialized,
        400: 'Bad request'
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def creer_adresse(request):
    adresses = Addresse.objects.filter(user=request.user)
    if adresses.count() >= NB_MAX_ADRESSES:
        return Response({"error": f"Vous ne pouvez pas avoir plus de {NB_MAX_ADRESSES} adresses."},
                        status=status.HTTP_400_BAD_REQUEST)
    serializer = AdresseSerialized(data=request.data)
    if serializer.is_valid():
        # La première adresse devient automatiquement l'adresse par défaut
        extra = {} if adresses.exists() else {'is_default': True}
        serializer.save(user=request.user, **extra)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#  Récupérer une adresse précise
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detail_adresse(request, pk):
    adresse = get_object_or_404(Addresse, pk=pk, user=request.user)
    serializer = AdresseSerialized(adresse)
    return Response(serializer.data, status=status.HTTP_200_OK)


#  Mettre à jour une adresse
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def modifier_adresse(request, pk):
    adresse = get_object_or_404(Addresse, pk=pk, user=request.user)
    serializer = AdresseSerialized(adresse, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#  Supprimer une adresse
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def supprimer_adresse(request, pk):
    adresse = get_object_or_404(Addresse, pk=pk, user=request.user)
    etait_defaut = adresse.is_default
    adresse.delete()
    if etait_defaut:
        # Une autre adresse prend le relais comme adresse par défaut
        suivante = Addresse.objects.filter(user=request.user).order_by('-created_at').first()
        if suivante:
            suivante.is_default = True
            suivante.save()
    return Response({"message": "Adresse supprimée avec succès."}, status=status.HTTP_204_NO_CONTENT)


#  Obtenir l'adresse par défaut
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def adresse_par_defaut(request):
    adresse = Addresse.objects.filter(user=request.user, is_default=True).order_by('-updated_at').first()
    if not adresse:
        return Response({"message": "Aucune adresse par défaut trouvée."}, status=status.HTTP_404_NOT_FOUND)
    serializer = AdresseSerialized(adresse)
    return Response(serializer.data, status=status.HTTP_200_OK)


#  Définir une adresse comme par défaut
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def definir_adresse_par_defaut(request, pk):
    adresse = get_object_or_404(Addresse, pk=pk, user=request.user)
    adresse.is_default = True
    adresse.save()  # le modèle retire automatiquement l'ancien « par défaut »
    return Response({"message": "Adresse par défaut mise à jour avec succès."}, status=status.HTTP_200_OK)
