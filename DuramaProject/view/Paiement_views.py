from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from ..models import Livraison, Commande,Paiement
from ..serializer import LivraisonSerialized,PaiementSerialized


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def creer_paiement(request, commande_id):
    try:
        commande = Commande.objects.get(id=commande_id, acheteur=request.user)
    except Commande.DoesNotExist:
        return Response({"message": "Commande introuvable ou non autorisée."}, status=status.HTTP_404_NOT_FOUND)

    serializer = PaiementSerialized(data=request.data)
    if serializer.is_valid():
        serializer.save(commande=commande)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def voir_paiement(request, paiement_id):
    try:
        paiement = Paiement.objects.select_related('commande').get(id=paiement_id)
    except Paiement.DoesNotExist:
        return Response({"message": "Paiement introuvable."}, status=status.HTTP_404_NOT_FOUND)

    if paiement.commande.acheteur != request.user and paiement.commande.vendeur != request.user:
        return Response({"message": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)

    serializer = PaiementSerialized(paiement)
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_paiement(request, paiement_id):
    try:
        paiement = Paiement.objects.get(id=paiement_id, commande__vendeur=request.user)
    except Paiement.DoesNotExist:
        return Response({"message": "Paiement introuvable ou non autorisé."}, status=status.HTTP_404_NOT_FOUND)

    serializer = PaiementSerialized(paiement, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def supprimer_paiement(request, paiement_id):
    try:
        paiement = Paiement.objects.get(id=paiement_id, commande__vendeur=request.user)
    except Paiement.DoesNotExist:
        return Response({"message": "Paiement introuvable ou non autorisé."}, status=status.HTTP_404_NOT_FOUND)

    paiement.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
