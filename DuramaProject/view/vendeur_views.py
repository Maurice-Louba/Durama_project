from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import Produit, Vendeur
from ..serializer import ProduitSerialized, VendeurSerialized


@api_view(["GET"])
@permission_classes([AllowAny])
def liste_vendeurs(request):
    vendeurs = Vendeur.objects.filter(actif=True).order_by("nom_boutique")
    serializer = VendeurSerialized(vendeurs, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
def detail_vendeur(request, slug):
    try:
        vendeur = Vendeur.objects.get(slug=slug, actif=True)
    except Vendeur.DoesNotExist:
        return Response(
            {"detail": "Vendeur introuvable."},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = VendeurSerialized(vendeur)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
def produits_vendeur(request, slug):
    try:
        vendeur = Vendeur.objects.get(slug=slug, actif=True)
    except Vendeur.DoesNotExist:
        return Response(
            {"detail": "Vendeur introuvable."},
            status=status.HTTP_404_NOT_FOUND
        )

    produits = Produit.objects.filter(
        vendeur=vendeur,
        est_publie=True
    ).select_related(
        'vendeur', 'categorie', 'sous_categorie__categorie_principale', 'etiquette'
    ).order_by("-created_at")

    serializer = ProduitSerialized(produits, many=True, context={'request': request})

    return Response(serializer.data, status=status.HTTP_200_OK)
