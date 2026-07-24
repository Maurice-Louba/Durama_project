from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from ..models import Vendeur, Produit
from ..serializer import VendeurSerialized, ProduitSerialized

@api_view(["GET"])
def liste_vendeurs(request):
    vendeurs = Vendeur.objects.filter(actif=True).order_by("nom_boutique")
    serializer = VendeurSerialized(vendeurs, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(["GET"])
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
    ).order_by("-created_at")

    serializer = ProduitSerialized(produits, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)