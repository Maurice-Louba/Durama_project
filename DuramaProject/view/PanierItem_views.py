from ..models import ContenuPanier,Panier
from django.shortcuts import render
from django.shortcuts import render
from rest_framework import generics,permissions
from ..serializer import PanierItemSerialized
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def panier_items(request):
    """
    - GET  : Récupérer tous les items du panier actif de l'utilisateur connecté
    - POST : Ajouter un produit dans le panier actif
    """
    
    # Récupérer ou créer le panier actif
    panier, _ = Panier.objects.get_or_create(user=request.user, actif=True)

    if request.method == 'GET':
        items = ContenuPanier.objects.filter(panier=panier)
        serializer = PanierItemSerialized(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        serializer = PanierItemSerialized(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(panier=panier)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def panier_item_detail(request, pk):
    # Récupérer le panier actif
    panier, _ = Panier.objects.get_or_create(user=request.user, actif=True)

    try:
        item = ContenuPanier.objects.get(pk=pk, panier=panier)
    except ContenuPanier.DoesNotExist:
        return Response({"error": "Item non trouvé dans le panier actif"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = PanierItemSerialized(item)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = PanierItemSerialized(item, data=request.data, partial=partial, context={'request': request})
        if serializer.is_valid():
            serializer.save(panier=panier)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


