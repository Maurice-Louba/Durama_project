from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from ..models import ProduitVariableAttribut, ProduitVariable, Attribut
from ..serializer import ProduitVariableAttributSerialized


# 1️Liste de toutes les associations ProduitVariable <-> Attribut
@api_view(['GET'])
@permission_classes([AllowAny])
def liste_produit_variable_attributs(request):
    liens = ProduitVariableAttribut.objects.all().order_by("-id")
    serializer = ProduitVariableAttributSerialized(liens, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# 2️ Associer un attribut à une variante
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ajouter_produit_variable_attribut(request):
    serializer = ProduitVariableAttributSerialized(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 3️ Obtenir les attributs d’une variante spécifique
@api_view(['GET'])
@permission_classes([AllowAny])
def attributs_par_variante(request, produit_variable_id):
    try:
        produit_var = ProduitVariable.objects.get(pk=produit_variable_id)
    except ProduitVariable.DoesNotExist:
        return Response({'error': 'Variante introuvable'}, status=status.HTTP_404_NOT_FOUND)

    liens = ProduitVariableAttribut.objects.filter(produit_variable=produit_var)
    serializer = ProduitVariableAttributSerialized(liens, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# 4️ Obtenir toutes les variantes d’un attribut donné
@api_view(['GET'])
@permission_classes([AllowAny])
def variantes_par_attribut(request, attribut_id):
    try:
        attr = Attribut.objects.get(pk=attribut_id)
    except Attribut.DoesNotExist:
        return Response({'error': 'Attribut introuvable'}, status=status.HTTP_404_NOT_FOUND)

    liens = ProduitVariableAttribut.objects.filter(attribut=attr)
    serializer = ProduitVariableAttributSerialized(liens, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# 5️ Supprimer un lien (dissocier un attribut d’une variante)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def supprimer_produit_variable_attribut(request, lien_id):
    try:
        lien = ProduitVariableAttribut.objects.get(pk=lien_id)
    except ProduitVariableAttribut.DoesNotExist:
        return Response({'error': 'Lien introuvable'}, status=status.HTTP_404_NOT_FOUND)

    lien.delete()
    return Response({'message': 'Association supprimée avec succès'}, status=status.HTTP_204_NO_CONTENT)
