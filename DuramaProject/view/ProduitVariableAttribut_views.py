from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from ..models import Attribut, Produit, ProduitVariableAttribut
from ..serializer import ProduitVariableAttributSerialized


def _liens():
    return ProduitVariableAttribut.objects.select_related(
        'attribut__typeAttribut',
        'produit_variable__produit__vendeur', 'produit_variable__produit__categorie',
        'produit_variable__produit__sous_categorie__categorie_principale', 'produit_variable__produit__etiquette',
    )


# 1️ Liste de toutes les associations ProduitVariable <-> Attribut
@api_view(['GET'])
@permission_classes([AllowAny])
def liste_produit_variable_attributs(request):
    liens = _liens().order_by("-id")
    serializer = ProduitVariableAttributSerialized(liens, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


# 2️ Associer un attribut à une variante
@api_view(['POST'])
@permission_classes([IsAdminUser])
def ajouter_produit_variable_attribut(request):
    serializer = ProduitVariableAttributSerialized(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 3️ Obtenir les attributs des variantes d'un produit (par slug du produit)
@api_view(['GET'])
@permission_classes([AllowAny])
def attributs_par_variante(request, slug):
    # Avant : .get(produit=produit) plantait (500) dès qu'un produit avait 2 variantes ou plus,
    # et un slug inconnu donnait aussi une erreur 500.
    if not Produit.objects.filter(slug=slug).exists():
        return Response({'error': 'Variante introuvable'}, status=status.HTTP_404_NOT_FOUND)

    liens = _liens().filter(produit_variable__produit__slug=slug)
    serializer = ProduitVariableAttributSerialized(liens, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


# 4️ Obtenir toutes les variantes d'un attribut donné
@api_view(['GET'])
@permission_classes([AllowAny])
def variantes_par_attribut(request, attribut_id):
    if not Attribut.objects.filter(pk=attribut_id).exists():
        return Response({'error': 'Attribut introuvable'}, status=status.HTTP_404_NOT_FOUND)

    liens = _liens().filter(attribut_id=attribut_id)
    serializer = ProduitVariableAttributSerialized(liens, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


# 5️ Supprimer un lien (dissocier un attribut d'une variante)
@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def supprimer_produit_variable_attribut(request, lien_id):
    try:
        lien = ProduitVariableAttribut.objects.get(pk=lien_id)
    except ProduitVariableAttribut.DoesNotExist:
        return Response({'error': 'Lien introuvable'}, status=status.HTTP_404_NOT_FOUND)

    lien.delete()
    return Response({'message': 'Association supprimée avec succès'}, status=status.HTTP_204_NO_CONTENT)
