from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ..models import SubCategorie, Categorie
from ..serializer import SousCategorieSerialized


#  1. Liste de toutes les sous-catégories
@api_view(['GET'])
@permission_classes([AllowAny])
def liste_souscategories(request):
    souscategories = SubCategorie.objects.all().order_by('nom')
    serializer = SousCategorieSerialized(souscategories, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


#  2. Récupérer les sous-catégories d’une catégorie donnée
@api_view(['GET'])
@permission_classes([AllowAny])
def souscategories_par_categorie(request, categorie_id):
    try:
        categorie = Categorie.objects.get(pk=categorie_id)
    except Categorie.DoesNotExist:
        return Response({"error": "Catégorie non trouvée"}, status=status.HTTP_404_NOT_FOUND)

    souscategories = SubCategorie.objects.filter(categorie_principale=categorie).order_by('nom')
    serializer = SousCategorieSerialized(souscategories, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


#  3. Détails d’une sous-catégorie
@api_view(['GET'])
@permission_classes([AllowAny])
def detail_souscategorie(request, souscategorie_id):
    try:
        souscategorie = SubCategorie.objects.get(pk=souscategorie_id)
    except SubCategorie.DoesNotExist:
        return Response({"error": "Sous-catégorie non trouvée"}, status=status.HTTP_404_NOT_FOUND)

    serializer = SousCategorieSerialized(souscategorie)
    return Response(serializer.data, status=status.HTTP_200_OK)


#  4. Créer une nouvelle sous-catégorie
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def creer_souscategorie(request, categorie_id):
    try:
        categorie = Categorie.objects.get(pk=categorie_id)
    except Categorie.DoesNotExist:
        return Response({"error": "Catégorie non trouvée"}, status=status.HTTP_404_NOT_FOUND)

    serializer = SousCategorieSerialized(data=request.data)
    if serializer.is_valid():
        serializer.save(categorie_principale=categorie)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 5. Modifier une sous-catégorie
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def modifier_souscategorie(request, souscategorie_id):
    try:
        souscategorie = SubCategorie.objects.get(pk=souscategorie_id)
    except SubCategorie.DoesNotExist:
        return Response({"error": "Sous-catégorie non trouvée"}, status=status.HTTP_404_NOT_FOUND)

    serializer = SousCategorieSerialized(souscategorie, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 6. Supprimer une sous-catégorie
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def supprimer_souscategorie(request, souscategorie_id):
    try:
        souscategorie = SubCategorie.objects.get(pk=souscategorie_id)
    except SubCategorie.DoesNotExist:
        return Response({"error": "Sous-catégorie non trouvée"}, status=status.HTTP_404_NOT_FOUND)

    souscategorie.delete()
    return Response({"message": "Sous-catégorie supprimée avec succès"}, status=status.HTTP_204_NO_CONTENT)
   