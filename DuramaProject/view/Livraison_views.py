from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from ..models import Commande, Livraison
from ..serializer import LivraisonSerialized

# NB : le modèle Commande n'a ni « acheteur » ni « vendeur » (ces vues plantaient à chaque appel).
# Le client est commande.user ; les livraisons sont gérées par le staff.


# Créer une livraison (admin)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def creer_livraison(request, commande_id=None):
    # La route « creer-une-livraison/ » n'a pas d'id dans l'URL : on le lit alors dans le corps
    commande_id = commande_id or request.data.get('commande_id')
    try:
        commande = Commande.objects.get(id=commande_id)
    except (Commande.DoesNotExist, ValueError, TypeError):
        return Response({"message": "Commande introuvable ou non autorisée."}, status=status.HTTP_404_NOT_FOUND)

    if commande.statut == 'annulee':
        return Response({"message": "Impossible de livrer une commande annulée."}, status=status.HTTP_400_BAD_REQUEST)

    serializer = LivraisonSerialized(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save(commande=commande)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Voir une livraison
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def voir_livraison(request, livraison_id):
    try:
        livraison = Livraison.objects.select_related('commande__user').get(id=livraison_id)
    except Livraison.DoesNotExist:
        return Response({"message": "Livraison introuvable."}, status=status.HTTP_404_NOT_FOUND)

    if livraison.commande.user_id != request.user.id and not request.user.is_staff:
        return Response({"message": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)

    serializer = LivraisonSerialized(livraison, context={'request': request})
    return Response(serializer.data)


# Mettre à jour une livraison
@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def update_livraison(request, livraison_id):
    try:
        livraison = Livraison.objects.get(id=livraison_id)
    except Livraison.DoesNotExist:
        return Response({"message": "Livraison introuvable ou non autorisée."}, status=status.HTTP_404_NOT_FOUND)

    serializer = LivraisonSerialized(livraison, data=request.data, partial=True, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Supprimer une livraison
@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def supprimer_livraison(request, livraison_id):
    try:
        livraison = Livraison.objects.get(id=livraison_id)
    except Livraison.DoesNotExist:
        return Response({"message": "Livraison introuvable ou non autorisée."}, status=status.HTTP_404_NOT_FOUND)

    livraison.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# Lister toutes les livraisons d'une commande
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lister_livraisons_commande(request, commande_id):
    try:
        commande = Commande.objects.get(id=commande_id)
    except Commande.DoesNotExist:
        return Response({"message": "Commande introuvable."}, status=status.HTTP_404_NOT_FOUND)

    if commande.user_id != request.user.id and not request.user.is_staff:
        return Response({"message": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)

    livraisons = Livraison.objects.filter(commande=commande)
    serializer = LivraisonSerialized(livraisons, many=True, context={'request': request})
    return Response(serializer.data)
