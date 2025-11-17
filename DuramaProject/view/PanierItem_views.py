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
        # Récupérer les données du produit à ajouter
        produit_id = request.data.get('produit')
        produit_variable_id = request.data.get('produit_variable')
        attribut_valeur_id = request.data.get('attribut_valeur')
        quantite = request.data.get('quantite', 1)
        
        # Vérifier si le produit existe déjà dans le panier
        items_existants = ContenuPanier.objects.filter(panier=panier, produit_id=produit_id)
        
        # Si c'est un produit variable, vérifier aussi le produit_variable et l'attribut
        if produit_variable_id:
            items_existants = items_existants.filter(
                produit_variable_id=produit_variable_id,
                attribut_valeur_id=attribut_valeur_id
            )
        
        item_existant = items_existants.first()
        
        if item_existant:
            # Si le produit existe déjà, augmenter la quantité
            item_existant.quantite += int(quantite)
            item_existant.save()
            
            # Sérialiser l'item mis à jour pour la réponse
            serializer = PanierItemSerialized(item_existant)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # Si le produit n'existe pas, créer un nouvel item
            serializer = PanierItemSerialized(data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save(panier=panier)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def deuxElementsDuPanier(request):
    panier, _ = Panier.objects.get_or_create(user=request.user, actif=True)
    try:
        contenu=ContenuPanier.objects.filter(panier=panier).order_by('-created_at')[:2]
    except Panier.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    contenuSeria=PanierItemSerialized(contenu,many=True)
    return Response(contenuSeria.data)    


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


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def total_panier(request):
    """
    Calcule le prix total du panier actif de l'utilisateur connecté.
    """
    # Récupérer le panier actif
    panier, _ = Panier.objects.get_or_create(user=request.user, actif=True)

    # Récupérer les éléments du panier
    contenu = ContenuPanier.objects.filter(panier=panier)

    # Calcul du total (en supposant que chaque item a un champ 'quantite' et 'produit.prix')
    total = 0
    for item in contenu:
        if item.produit.prix_promo==0:
            total += item.produit.prix_vente*item.quantite
        else :
            total += item.produit.prix_promo*item.quantite
            

    return Response( total, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def augmenter_quantite(request,pk):
    try:
        panier_it=ContenuPanier.objects.get(pk=pk)
    except ContenuPanier.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    panier_it.quantite +=1
    panier_it.save()
    return Response({"message": "Quantité mise à jour avec succès ✅"})

@api_view(['POST'])
@permission_classes([AllowAny])
def dimunuer_quantite(request,pk):
    try:
        panier_it=ContenuPanier.objects.get(pk=pk)
    except ContenuPanier.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if panier_it.quantite > 1:
        panier_it.quantite -=1
        panier_it.save()
    return Response({"message": "Quantité mise à jour avec succès ✅"})

@api_view(['DELETE'])
@permission_classes([AllowAny])
def supprimer_item(request,pk):
    try:
        item=ContenuPanier.objects.get(pk=pk)
    except ContenuPanier.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    item.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)



@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def vider_panier(request):
    """
    Supprimer tous les éléments du panier actif de l'utilisateur connecté.
    """
    panier, _ = Panier.objects.get_or_create(user=request.user, actif=True)
    items = ContenuPanier.objects.filter(panier=panier)

    if not items.exists():
        return Response({"message": "Le panier est déjà vide 🧺"}, status=status.HTTP_200_OK)
    items.delete()

    return Response({"message": "Le panier a été vidé avec succès 🧹"}, status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nombre_element_panier(request):
    try:
        panier = Panier.objects.get(user=request.user,actif=True)
    except Panier.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    itemsNombre=ContenuPanier.objects.filter(panier=panier).count()
    return Response(itemsNombre)
