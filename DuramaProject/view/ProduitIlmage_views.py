from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ..models import ImageProduit, Produit
from ..serializer import ImageProduitSerialized


#  1. Liste de toutes les images
@api_view(['GET'])
@permission_classes([AllowAny])
def liste_images(request):
    images = ImageProduit.objects.all().order_by('-created_at')
    serializer = ImageProduitSerialized(images, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


#  2. Récupérer toutes les images d’un produit précis
@api_view(['GET'])
@permission_classes([AllowAny])
def images_par_produit(request, produit_id):
    try:
        produit = Produit.objects.get(pk=produit_id)
    except Produit.DoesNotExist:
        return Response({'error': 'Produit introuvable'}, status=status.HTTP_404_NOT_FOUND)

    images = ImageProduit.objects.filter(produit=produit).order_by('-created_at')
    serializer = ImageProduitSerialized(images, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


#  3. Ajouter une nouvelle image à un produit
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ajouter_image(request, produit_id):
    try:
        produit = Produit.objects.get(pk=produit_id)
    except Produit.DoesNotExist:
        return Response({'error': 'Produit introuvable'}, status=status.HTTP_404_NOT_FOUND)

    data = request.data.copy()
    data['produit'] = produit.id  # on associe l’image au produit

    serializer = ImageProduitSerialized(data=data)
    if serializer.is_valid():
        serializer.save(produit=produit)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#  4. Détails d’une image spécifique
@api_view(['GET'])
@permission_classes([AllowAny])
def details_image(request, image_id):
    try:
        image = ImageProduit.objects.get(pk=image_id)
    except ImageProduit.DoesNotExist:
        return Response({'error': 'Image introuvable'}, status=status.HTTP_404_NOT_FOUND)

    serializer = ImageProduitSerialized(image)
    return Response(serializer.data, status=status.HTTP_200_OK)


#  5. Supprimer une image
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def supprimer_image(request, image_id):
    try:
        image = ImageProduit.objects.get(pk=image_id)
    except ImageProduit.DoesNotExist:
        return Response({'error': 'Image introuvable'}, status=status.HTTP_404_NOT_FOUND)

    image.delete()
    return Response({'message': 'Image supprimée avec succès'}, status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([AllowAny])
def images_un_produit(request,slug):
    try:
        produit=Produit.objects.get(slug=slug)
    except Produit.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    images=ImageProduit.objects.filter(produit=produit)
    serializer=ImageProduitSerialized(images,many=True)
    return Response(serializer.data)