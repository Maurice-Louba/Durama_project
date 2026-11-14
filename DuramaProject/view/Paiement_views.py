from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from ..models import Commande, Paiement
from ..serializer import PaiementAdminSerialized, PaiementSerialized

# NB : le modèle Commande n'a ni « acheteur » ni « vendeur » (ces vues plantaient à chaque appel).
# Le client est commande.user ; la validation des paiements est faite par le staff.


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def creer_paiement(request, commande_id):
    try:
        commande = Commande.objects.get(id=commande_id, user=request.user)
    except Commande.DoesNotExist:
        return Response({"message": "Commande introuvable ou non autorisée."}, status=status.HTTP_404_NOT_FOUND)

    serializer = PaiementSerialized(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save(commande=commande)  # le montant est imposé par le serveur
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def voir_paiement(request, paiement_id):
    try:
        paiement = Paiement.objects.select_related('commande__user').get(id=paiement_id)
    except Paiement.DoesNotExist:
        return Response({"message": "Paiement introuvable."}, status=status.HTTP_404_NOT_FOUND)

    if paiement.commande.user_id != request.user.id and not request.user.is_staff:
        return Response({"message": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)

    serializer = PaiementSerialized(paiement, context={'request': request})
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def update_paiement(request, paiement_id):
    try:
        paiement = Paiement.objects.get(id=paiement_id)
    except Paiement.DoesNotExist:
        return Response({"message": "Paiement introuvable ou non autorisé."}, status=status.HTTP_404_NOT_FOUND)

    serializer = PaiementAdminSerialized(paiement, data=request.data, partial=True, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def supprimer_paiement(request, paiement_id):
    try:
        paiement = Paiement.objects.get(id=paiement_id)
    except Paiement.DoesNotExist:
        return Response({"message": "Paiement introuvable ou non autorisé."}, status=status.HTTP_404_NOT_FOUND)

    if paiement.statut == 'effectue':
        return Response({"message": "Un paiement effectué ne peut pas être supprimé."}, status=status.HTTP_400_BAD_REQUEST)
    paiement.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
