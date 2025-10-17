from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from ..models import ProduitVariable, ProduitVariableImage
from ..serializer import ProduitVariableImageSerialized


# 1️ Liste de toutes les images de variantes
@api_view(['GET'])
@permission_classes([AllowAny])
def liste_variante_images(request):
    images = ProduitVariableImage.objects.all().order_by("-created_at")
    serializer = ProduitVariableImageSerialized(images, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# 2️ Toutes les images d’une variante donnée
@api_view(['GET'])
@permission_classes([AllowAny])
def images_par_variante(request, produit_variable_id):
    try:
        variante = ProduitVariable.objects.get(pk=produit_variable_id)
    except ProduitVariable.DoesNotExist:
        return Response({'error': 'Variante introuvable'}, status=status.HTTP_404_NOT_FOUND)

    images = ProduitVariableImage.objects.filter(produit_variable=variante).order_by("-created_at")
    serializer = ProduitVariableImageSerialized(images, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# 3️ Ajouter une image à une variante
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ajouter_variante_image(request, produit_variable_id):
    try:
        variante = ProduitVariable.objects.get(pk=produit_variable_id)
    except ProduitVariable.DoesNotExist:
        return Response({'error': 'Variante introuvable'}, status=status.HTTP_404_NOT_FOUND)

    data = request.data.copy()
    data['produit_variable'] = variante.id

    serializer = ProduitVariableImageSerialized(data=data)
    if serializer.is_valid():
        serializer.save(produit_variable=variante)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 4️ Détails d’une image précise
@api_view(['GET'])
@permission_classes([AllowAny])
def details_variante_image(request, image_id):
    try:
        image = ProduitVariableImage.objects.get(pk=image_id)
    except ProduitVariableImage.DoesNotExist:
        return Response({'error': 'Image introuvable'}, status=status.HTTP_404_NOT_FOUND)

    serializer = ProduitVariableImageSerialized(image)
    return Response(serializer.data, status=status.HTTP_200_OK)


# 5️ Supprimer une image de variante
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def supprimer_variante_image(request, image_id):
    try:
        image = ProduitVariableImage.objects.get(pk=image_id)
    except ProduitVariableImage.DoesNotExist:
        return Response({'error': 'Image introuvable'}, status=status.HTTP_404_NOT_FOUND)

    image.delete()
    return Response({'message': 'Image supprimée avec succès'}, status=status.HTTP_204_NO_CONTENT)
