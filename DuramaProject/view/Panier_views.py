from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Panier
from ..serializer import PanierSerialized


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def liste_paniers(request):
    paniers = Panier.objects.filter(user=request.user).select_related('user').order_by('-created_at')
    serializer = PanierSerialized(paniers, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def creer_panier(request):
    # Un seul panier actif par utilisateur : renvoie le panier actif existant s'il y en a un
    serializer = PanierSerialized(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def panier_detail(request, pk):
    panier = get_object_or_404(Panier, pk=pk, user=request.user)

    if request.method == 'GET':
        serializer = PanierSerialized(panier)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = PanierSerialized(panier, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE : un panier déjà transformé en commande est conservé (historique de la commande)
    if not panier.actif:
        return Response({'error': 'Ce panier est lié à une commande et ne peut pas être supprimé.'},
                        status=status.HTTP_400_BAD_REQUEST)
    panier.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
