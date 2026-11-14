from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from ..models import ImageProduit, Produit
from ..serializer import ImageProduitSerialized

TAILLE_MAX_IMAGE = 5 * 1024 * 1024  # 5 Mo


def _images():
    return ImageProduit.objects.select_related(
        'produit__vendeur', 'produit__categorie', 'produit__sous_categorie__categorie_principale', 'produit__etiquette'
    )


#  1. Liste de toutes les images
@api_view(['GET'])
@permission_classes([AllowAny])
def liste_images(request):
    images = _images().order_by('-created_at')
    serializer = ImageProduitSerialized(images, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


#  2. Récupérer toutes les images d'un produit précis
@api_view(['GET'])
@permission_classes([AllowAny])
def images_par_produit(request, produit_id):
    if not Produit.objects.filter(pk=produit_id).exists():
        return Response({'error': 'Produit introuvable'}, status=status.HTTP_404_NOT_FOUND)

    images = _images().filter(produit_id=produit_id).order_by('-created_at')
    serializer = ImageProduitSerialized(images, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


#  3. Ajouter une nouvelle image à un produit
@api_view(['POST'])
@permission_classes([IsAdminUser])
def ajouter_image(request, produit_id):
    try:
        produit = Produit.objects.get(pk=produit_id)
    except Produit.DoesNotExist:
        return Response({'error': 'Produit introuvable'}, status=status.HTTP_404_NOT_FOUND)

    fichier = request.FILES.get('image')
    if fichier is not None and fichier.size > TAILLE_MAX_IMAGE:
        return Response({'image': ["L'image ne doit pas dépasser 5 Mo."]}, status=status.HTTP_400_BAD_REQUEST)

    serializer = ImageProduitSerialized(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save(produit=produit)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#  4. Détails d'une image spécifique
@api_view(['GET'])
@permission_classes([AllowAny])
def details_image(request, image_id):
    try:
        image = _images().get(pk=image_id)
    except ImageProduit.DoesNotExist:
        return Response({'error': 'Image introuvable'}, status=status.HTTP_404_NOT_FOUND)

    serializer = ImageProduitSerialized(image, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


#  5. Supprimer une image
@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def supprimer_image(request, image_id):
    try:
        image = ImageProduit.objects.get(pk=image_id)
    except ImageProduit.DoesNotExist:
        return Response({'error': 'Image introuvable'}, status=status.HTTP_404_NOT_FOUND)

    image.image.delete(save=False)  # supprime aussi le fichier sur le disque
    image.delete()
    return Response({'message': 'Image supprimée avec succès'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([AllowAny])
def images_un_produit(request, slug):
    if not Produit.objects.filter(slug=slug).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)
    images = _images().filter(produit__slug=slug)
    serializer = ImageProduitSerialized(images, many=True, context={'request': request})
    return Response(serializer.data)
