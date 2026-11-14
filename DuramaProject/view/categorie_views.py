from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from ..models import Categorie
from ..serializer import CategorieSerialized


@api_view(['POST'])
@permission_classes([IsAdminUser])
def createCategorie(request):
    categorie = CategorieSerialized(data=request.data)
    if categorie.is_valid():
        categorie.save()
        return Response(categorie.data, status=status.HTTP_201_CREATED)
    return Response(categorie.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminUser])
def changeCategorie(request, categorie_id):
    try:
        categorie = Categorie.objects.get(id=categorie_id)
    except Categorie.DoesNotExist:
        return Response({"detail": "Catégorie non trouvée"}, status=status.HTTP_404_NOT_FOUND)

    serializer = CategorieSerialized(categorie, data=request.data, partial=(request.method == 'PATCH'))
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def SupprimerCategorie(request, categorie_id):
    try:
        categorie = Categorie.objects.get(pk=categorie_id)
    except Categorie.DoesNotExist:
        return Response({'error': 'cette categorie existe pas'}, status=status.HTTP_404_NOT_FOUND)
    if categorie.produits.exists():
        # Le CASCADE supprimerait aussi tous les produits de la catégorie
        return Response(
            {'error': "Cette catégorie contient des produits : déplacez-les ou supprimez-les d'abord"},
            status=status.HTTP_409_CONFLICT,
        )
    categorie.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([AllowAny])
def TousLesCategories(request):
    categorie = Categorie.objects.all().order_by('nom')
    categorieSeriali = CategorieSerialized(categorie, many=True)
    return Response(categorieSeriali.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def DetailCategorie(request, pk):
    try:
        categories = Categorie.objects.get(pk=pk)
    except Categorie.DoesNotExist:
        return Response({'error': 'categorie non trouvé'}, status=status.HTTP_404_NOT_FOUND)
    categoriesSeria = CategorieSerialized(categories)
    return Response(categoriesSeria.data)


# Liste des catégorie selon le type de gros categorie
@api_view(['GET'])
@permission_classes([AllowAny])
def toutCategories(request, groCategorie):
    grosCategorie = Categorie.objects.filter(gros_categorie=groCategorie).order_by('nom')
    grosCategorieserial = CategorieSerialized(grosCategorie, many=True)
    return Response(grosCategorieserial.data)
