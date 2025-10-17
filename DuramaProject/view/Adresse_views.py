# views_adresse.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from ..models import Addresse
from ..serializer import AdresseSerialized
from drf_yasg.utils import swagger_auto_schema

#  Liste toutes les adresses de l'utilisateur connecté
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def liste_adresses(request):
    adresses = Addresse.objects.filter(user=request.user)
    serializer = AdresseSerialized(adresses, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# Créer une nouvelle adresse
@swagger_auto_schema(
    method='post',
    request_body=AdresseSerialized,
    reponses={
        201: AdresseSerialized,
        404:'Bad request'
        
        
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def creer_adresse(request):
    serializer = AdresseSerialized(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
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
    adresse.delete()
    return Response({"message": "Adresse supprimée avec succès."}, status=status.HTTP_204_NO_CONTENT)


#  Obtenir l’adresse par défaut
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def adresse_par_defaut(request):
    adresse = Addresse.objects.filter(user=request.user, is_default=True).first()
    if not adresse:
        return Response({"message": "Aucune adresse par défaut trouvée."}, status=status.HTTP_404_NOT_FOUND)
    serializer = AdresseSerialized(adresse)
    return Response(serializer.data, status=status.HTTP_200_OK)


#  Définir une adresse comme par défaut
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def definir_adresse_par_defaut(request, pk):
    adresse = get_object_or_404(Addresse, pk=pk, user=request.user)
    # Retirer l’ancien “is_default”
    Addresse.objects.filter(user=request.user, is_default=True).update(is_default=False)
    adresse.is_default = True
    adresse.save()
    return Response({"message": "Adresse par défaut mise à jour avec succès."}, status=status.HTTP_200_OK)
