from ..models import Favori,Produit
from django.shortcuts import render
from django.shortcuts import render
from rest_framework import generics,permissions
from ..serializer import FavoriSerialized
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ajouter_produit_comme_favorie(request,produit_id):
    try:
        produit=Produit.objects.get(produit_id=produit_id)
    except Produit.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    data=FavoriSerialized(data=request.data,context={'request':request})
    if data.is_valid():
        data.save(produit=produit)
        return Response(status=status.HTTP_201_CREATED)
    return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsADirectoryError])
def voir_produit_Favorie(request):
    try:
        favorie=Favori.objects.filter(user=request.user)
    except Favori.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    favorieSeria=FavoriSerialized(favorie,many=True)
    return Response(favorieSeria.data)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def supprimer_favorie(request,pk):
    try:
        favori=Favori.objects.get(pk=pk,user=request.user)
    except Favori.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    favori.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


#Nombre de favorie

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nombre_de_favorie(request):
    try:
        nombreFavoris=Favori.objects.filter(user=request.user).count()
    except Favori.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(nombreFavoris)