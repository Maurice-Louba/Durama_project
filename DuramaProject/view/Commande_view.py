from ..models import Commande,Panier,CommandeItem
from django.shortcuts import render
from django.shortcuts import render
from rest_framework import generics,permissions
from ..serializer import CommandeSerialized
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def faire_une_commande(request):
    try:
        panier = Panier.objects.get(user=request.user, actif=True)
    except Panier.DoesNotExist:
        return Response({'message': 'Aucun panier actif'}, status=status.HTTP_404_NOT_FOUND)

    # Création de la commande
    commande = Commande.objects.create(
        user=request.user,
        panier=panier,
          
    )

    # Copier le contenu du panier dans les CommandeItem
    for item in panier.contenu.all():
        CommandeItem.objects.create(
            commande=commande,
            produit=item.produit,
            produit_variable=item.produit_variable,
            quantite=item.quantite,
            prix_unitaire=item.produit_variable.prix_vente if item.is_variable else item.produit.prix_vente
        )

    # Calculer les totaux
    commande.calculer_totaux()

    # Fermer le panier
    panier.actif = False
    panier.save()

    return Response(CommandeSerialized(commande).data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tous_les_commandes(request):
    commandes=Commande.objects.all().order_by('-created_at')
    commandesSerial=CommandeSerialized(commandes,many=True)
    return Response(commandesSerial.data)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def commandeParUser(request,user_id):
    try:
        commandes=Commande.objects.filter(user_id=user_id)
    except Commande.DoesNotExist:
        return Response({'message':'ce utilisateur a aucune commande'},status=status.HTTP_400_BAD_REQUEST)
    commandesSeria=CommandeSerialized(commandes,many=True)
    return Response(commandesSeria.data)
@api_view(['PUT','PATCH'])
@permission_classes([IsAuthenticated])
def changerUneCommande(request,pk):
    try:
        commande=Commande.objects.get(pk=pk)
    except Commande.DoesNotExist:
        return Response({'error':'commande inexistante'})
    data=CommandeSerialized(data=request,partial=(request.method=='PATCH'))
    if data.is_valid():
        data.save(commande=commande)
        return Response(status=status.HTTP_201_CREATED)
    return Response(status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def commandeParUser(request,user_id):
    try:
        commandes=Commande.objects.filter(user_id=user_id)
    except Commande.DoesNotExist:
        return Response({'message':'ce utilisateur a aucune commande'},status=status.HTTP_400_BAD_REQUEST)
    commandesSeria=CommandeSerialized(commandes,many=True)
    return Response(commandesSeria.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nombre_commande(request):
    try:
        nombreCommande = Commande.objects.filter(user=request.user).count()
    except Commande.DoesNotExist:
        return Response({'message':"utilisateur non trouver"})
    return Response(nombreCommande)
