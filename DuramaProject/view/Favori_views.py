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
def ajouter_produit_comme_favorie(request, produit_id):
    try:
        produit = Produit.objects.get(pk=produit_id)
    except Produit.DoesNotExist:
        return Response({'error': 'Produit introuvable'}, status=status.HTTP_404_NOT_FOUND)

    # 🔎 Vérifier si le produit est déjà dans les favoris de l'utilisateur
    favori_existe = Favori.objects.filter(user=request.user, produit=produit).exists()
    if favori_existe:
        return Response({'message': 'Ce produit est déjà dans vos favoris.'}, status=status.HTTP_200_OK)

    # ✅ Ajouter si ce n’est pas encore fait
    data = FavoriSerialized(data=request.data, context={'request': request})
    if data.is_valid():
        data.save(produit=produit, user=request.user)
        return Response({'message': 'Produit ajouté aux favoris.'}, status=status.HTTP_201_CREATED)

    return Response(data.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET'])
@permission_classes([AllowAny])
def voir_produit_Favorie(request):
    try:
        favorie=Favori.objects.filter(user=request.user)
    except Favori.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    favorieSeria=FavoriSerialized(favorie,many=True)
    return Response(favorieSeria.data)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def supprimer_favorie(request,produit_id):
    try:
        produit=Produit.objects.get(pk=produit_id)
    except Favori.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    favori=Favori.objects.get(produit=produit,user=request.user)
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verification_existance(request,produit_id):
    try:
        produit=Produit.objects.get(id=produit_id)
    except Produit.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    resultat = Favori.objects.filter(produit=produit,user=request.user).exists()
    return Response({'existe': resultat})