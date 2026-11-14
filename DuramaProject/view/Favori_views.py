from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Favori, Produit
from ..serializer import FavoriSerialized


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ajouter_produit_comme_favorie(request, produit_id):
    try:
        produit = Produit.objects.get(pk=produit_id)
    except Produit.DoesNotExist:
        return Response({'error': 'Produit introuvable'}, status=status.HTTP_404_NOT_FOUND)

    # 🔎 Vérifier si le produit est déjà dans les favoris de l'utilisateur
    if Favori.objects.filter(user=request.user, produit=produit).exists():
        return Response({'message': 'Ce produit est déjà dans vos favoris.'}, status=status.HTTP_200_OK)

    # ✅ Ajouter si ce n'est pas encore fait
    data = FavoriSerialized(data=request.data, context={'request': request})
    if data.is_valid():
        data.save(produit=produit, user=request.user)
        return Response({'message': 'Produit ajouté aux favoris.'}, status=status.HTTP_201_CREATED)

    return Response(data.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])  # avant AllowAny : un visiteur anonyme provoquait une erreur 500
def voir_produit_Favorie(request):
    favorie = Favori.objects.filter(user=request.user).select_related(
        'user', 'produit__vendeur', 'produit__categorie',
        'produit__sous_categorie__categorie_principale', 'produit__etiquette',
    ).order_by('-created_at')
    favorieSeria = FavoriSerialized(favorie, many=True, context={'request': request})
    return Response(favorieSeria.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def supprimer_favorie(request, produit_id):
    supprimes, _ = Favori.objects.filter(produit_id=produit_id, user=request.user).delete()
    if not supprimes:
        return Response({'error': 'Favori introuvable'}, status=status.HTTP_404_NOT_FOUND)
    return Response(status=status.HTTP_204_NO_CONTENT)


# Nombre de favorie
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nombre_de_favorie(request):
    return Response(Favori.objects.filter(user=request.user).count())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verification_existance(request, produit_id):
    if not Produit.objects.filter(id=produit_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)
    resultat = Favori.objects.filter(produit_id=produit_id, user=request.user).exists()
    return Response({'existe': resultat})
