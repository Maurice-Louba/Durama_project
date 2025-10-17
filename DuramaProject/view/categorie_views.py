from ..models import Categorie
from django.shortcuts import render
from django.shortcuts import render
from rest_framework import generics,permissions
from ..serializer import CategorieSerialized
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def createCategorie(request):
    categorie=CategorieSerialized(data=request.data)
    if categorie.is_valid():
        categorie.save()
        return Response(status=status.HTTP_201_CREATED)
    return Response(status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def changeCategorie(request, categorie_id):
    try:
        categorie = Categorie.objects.get(id=categorie_id)
    except Categorie.DoesNotExist:
        return Response({"detail": "Catégorie non trouvée"}, status=status.HTTP_404_NOT_FOUND)

    serializer = CategorieSerialized(categorie, data=request.data, partial=(request.method=='PATCH'))
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def SupprimerCategorie(request,categorie_id):
    try:
        categorie=Categorie.objects.get(pk=categorie_id)
    except Categorie.DoesNotExist:
        return Response({'error':'cette categorie existe pas'},status=status.HTTP_404_NOT_FOUND)
    categorie.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
@api_view(["GET"])
@permission_classes([AllowAny])
def TousLesCategories(request):
    categorie=Categorie.objects.all().order_by('nom')
    categorieSeriali=CategorieSerialized(categorie,many=True)
    return Response(categorieSeriali.data)
@api_view(['GET'])
@permission_classes([AllowAny])
def DetailCategorie(request,pk):
    try:
        categories = Categorie.objects.get(pk=pk)
    except Categorie.DoesNotExist:
        return Response({'error':'categorie non trouvé'},status=status.HTTP_404_NOT_FOUND)
    categoriesSeria=CategorieSerialized(categories)
    return Response(categoriesSeria.data)

#Liste des catégorie selon le type de gros categorie
@api_view(['GET'])
@permission_classes([AllowAny])
def toutCategories(request,groCategorie):
    try:
        grosCategorie=Categorie.objects.filter(gros_categorie=groCategorie)
    except Categorie.DoesNotExist:
        return Response({"message":"ces categories n'existent pas "},status=status.HTTP_404_NOT_FOUND)
    grosCategorieserial=CategorieSerialized(grosCategorie,many=True)
    return Response(grosCategorieserial.data)