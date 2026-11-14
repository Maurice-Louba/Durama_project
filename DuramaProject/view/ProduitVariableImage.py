from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from ..models import ProduitVariable, ProduitVariableImage
from ..serializer import ProduitVariableImageSerialized

TAILLE_MAX_IMAGE = 5 * 1024 * 1024  # 5 Mo


def _images():
    return ProduitVariableImage.objects.select_related(
        'produit_variable__produit__vendeur', 'produit_variable__produit__categorie',
        'produit_variable__produit__sous_categorie__categorie_principale', 'produit_variable__produit__etiquette',
    )


# 1️ Liste de toutes les images de variantes
@api_view(['GET'])
@permission_classes([AllowAny])
def liste_variante_images(request):
    images = _images().order_by("-created_at")
    serializer = ProduitVariableImageSerialized(images, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


# 2️ Toutes les images d'une variante donnée
@api_view(['GET'])
@permission_classes([AllowAny])
def images_par_variante(request, produit_variable_id):
    if not ProduitVariable.objects.filter(pk=produit_variable_id).exists():
        return Response({'error': 'Variante introuvable'}, status=status.HTTP_404_NOT_FOUND)

    images = _images().filter(produit_variable_id=produit_variable_id).order_by("-created_at")
    serializer = ProduitVariableImageSerialized(images, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


# 3️ Ajouter une image à une variante
@api_view(['POST'])
@permission_classes([IsAdminUser])
def ajouter_variante_image(request, produit_variable_id):
    try:
        variante = ProduitVariable.objects.get(pk=produit_variable_id)
    except ProduitVariable.DoesNotExist:
        return Response({'error': 'Variante introuvable'}, status=status.HTTP_404_NOT_FOUND)

    fichier = request.FILES.get('image')
    if fichier is not None and fichier.size > TAILLE_MAX_IMAGE:
        return Response({'image': ["L'image ne doit pas dépasser 5 Mo."]}, status=status.HTTP_400_BAD_REQUEST)

    serializer = ProduitVariableImageSerialized(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save(produit_variable=variante)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 4️ Détails d'une image précise
@api_view(['GET'])
@permission_classes([AllowAny])
def details_variante_image(request, image_id):
    try:
        image = _images().get(pk=image_id)
    except ProduitVariableImage.DoesNotExist:
        return Response({'error': 'Image introuvable'}, status=status.HTTP_404_NOT_FOUND)

    serializer = ProduitVariableImageSerialized(image, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


# 5️ Supprimer une image de variante
@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def supprimer_variante_image(request, image_id):
    try:
        image = ProduitVariableImage.objects.get(pk=image_id)
    except ProduitVariableImage.DoesNotExist:
        return Response({'error': 'Image introuvable'}, status=status.HTTP_404_NOT_FOUND)

    image.image.delete(save=False)
    image.delete()
    return Response({'message': 'Image supprimée avec succès'}, status=status.HTTP_204_NO_CONTENT)
