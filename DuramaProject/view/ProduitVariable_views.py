from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from ..models import ProduitVariable, Produit
from ..serializer import ProduitVariableSerialized


#  1. Liste de toutes les variantes
@api_view(['GET'])
@permission_classes([AllowAny])
def liste_variantes(request):
    variantes = ProduitVariable.objects.all().order_by('-created_at')
    serializer = ProduitVariableSerialized(variantes, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


#  2. Variantes d’un produit spécifique
@api_view(['GET'])
@permission_classes([AllowAny])
def variantes_par_produit(request, produit_id):
    try:
        produit = Produit.objects.get(pk=produit_id)
    except Produit.DoesNotExist:
        return Response({'error': 'Produit introuvable'}, status=status.HTTP_404_NOT_FOUND)

    variantes = ProduitVariable.objects.filter(produit=produit).order_by('-created_at')
    serializer = ProduitVariableSerialized(variantes, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


#  3. Ajouter une variante à un produit
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ajouter_variante(request, produit_id):
    try:
        produit = Produit.objects.get(pk=produit_id)
    except Produit.DoesNotExist:
        return Response({'error': 'Produit introuvable'}, status=status.HTTP_404_NOT_FOUND)

    data = request.data.copy()
    data['produit'] = produit.id

    serializer = ProduitVariableSerialized(data=data)
    if serializer.is_valid():
        serializer.save(produit=produit)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#  4. Détails d’une variante spécifique
@api_view(['GET'])
@permission_classes([AllowAny])
def details_variante(request, variante_id):
    try:
        variante = ProduitVariable.objects.get(pk=variante_id)
    except ProduitVariable.DoesNotExist:
        return Response({'error': 'Variante introuvable'}, status=status.HTTP_404_NOT_FOUND)

    serializer = ProduitVariableSerialized(variante)
    return Response(serializer.data, status=status.HTTP_200_OK)


#  5. Modifier une variante
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def modifier_variante(request, variante_id):
    try:
        variante = ProduitVariable.objects.get(pk=variante_id)
    except ProduitVariable.DoesNotExist:
        return Response({'error': 'Variante introuvable'}, status=status.HTTP_404_NOT_FOUND)

    serializer = ProduitVariableSerialized(variante, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#  6. Supprimer une variante
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def supprimer_variante(request, variante_id):
    try:
        variante = ProduitVariable.objects.get(pk=variante_id)
    except ProduitVariable.DoesNotExist:
        return Response({'error': 'Variante introuvable'}, status=status.HTTP_404_NOT_FOUND)

    variante.delete()
    return Response({'message': 'Variante supprimée avec succès'}, status=status.HTTP_204_NO_CONTENT)
