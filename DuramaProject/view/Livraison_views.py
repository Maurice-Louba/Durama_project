from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from ..models import Livraison, Commande
from ..serializer import LivraisonSerialized


#Créer une livraison (par le vendeur ou admin)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def creer_livraison(request, commande_id):
    try:
        commande = Commande.objects.get(id=commande_id, vendeur=request.user)
    except Commande.DoesNotExist:
        return Response({"message": "Commande introuvable ou non autorisée."}, status=status.HTTP_404_NOT_FOUND)

    serializer = LivraisonSerialized(data=request.data)
    if serializer.is_valid():
        serializer.save(commande=commande)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#Voir une livraison
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def voir_livraison(request, livraison_id):
    try:
        livraison = Livraison.objects.select_related('commande').get(id=livraison_id)
    except Livraison.DoesNotExist:
        return Response({"message": "Livraison introuvable."}, status=status.HTTP_404_NOT_FOUND)

    if livraison.commande.acheteur != request.user and livraison.commande.vendeur != request.user:
        return Response({"message": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)

    serializer = LivraisonSerialized(livraison)
    return Response(serializer.data)




#Mettre à jour une livraison
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_livraison(request, livraison_id):
    try:
        livraison = Livraison.objects.get(id=livraison_id, commande__vendeur=request.user)
    except Livraison.DoesNotExist:
        return Response({"message": "Livraison introuvable ou non autorisée."}, status=status.HTTP_404_NOT_FOUND)

    serializer = LivraisonSerialized(livraison, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#Supprimer un paiement
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def supprimer_livraison(request, livraison_id):
    try:
        livraison = Livraison.objects.get(id=livraison_id, commande__vendeur=request.user)
    except Livraison.DoesNotExist:
        return Response({"message": "Livraison introuvable ou non autorisée."}, status=status.HTTP_404_NOT_FOUND)

    livraison.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


#Lister toutes les livraisons d’une commande
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lister_livraisons_commande(request, commande_id):
    try:
        commande = Commande.objects.get(id=commande_id)
    except Commande.DoesNotExist:
        return Response({"message": "Commande introuvable."}, status=status.HTTP_404_NOT_FOUND)

    if commande.acheteur != request.user and commande.vendeur != request.user:
        return Response({"message": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)

    livraisons = Livraison.objects.filter(commande=commande)
    serializer = LivraisonSerialized(livraisons, many=True)
    return Response(serializer.data)
