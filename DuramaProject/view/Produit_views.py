from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from ..models import Categorie, Etiquette, Produit, SubCategorie
from ..serializer import ProduitSerialized


def produits_visibles(request):
    """Le public ne voit que les produits publiés ; le staff voit tout (back-office)."""
    qs = Produit.objects.select_related(
        'vendeur', 'categorie', 'sous_categorie__categorie_principale', 'etiquette'
    )
    if not (request.user and request.user.is_staff):
        qs = qs.filter(est_publie=True)
    return qs


def repondre(request, produits, many=True, code=status.HTTP_200_OK):
    serializer = ProduitSerialized(produits, many=many, context={'request': request})
    return Response(serializer.data, status=code)


#  1. Liste de tous les produits (option tri / recherche simple)
@api_view(['GET'])
@permission_classes([AllowAny])
def liste_produits(request):
    return repondre(request, produits_visibles(request).order_by("nom"))


@api_view(['GET'])
@permission_classes([AllowAny])
def TousLesProduitsAleatoirement(request):
    # Récupération aléatoire des produits
    return repondre(request, produits_visibles(request).order_by('?'))


#  2. Détail d'un produit
@api_view(['GET'])
@permission_classes([AllowAny])
def detail_produit(request, slug):
    try:
        produit = produits_visibles(request).get(slug=slug)
    except Produit.DoesNotExist:
        return Response({"error": "Produit non trouvé"}, status=status.HTTP_404_NOT_FOUND)
    if not request.user.is_staff:
        produit.increment_views()  # On incrémente le compteur de vues à chaque affichage client
    return repondre(request, produit, many=False)


#  3. Créer un produit
@api_view(['POST'])
@permission_classes([IsAdminUser])
def creer_produit(request):
    serializer = ProduitSerialized(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()  # Les champs categorie_id, sous_categorie_id et etiquette_id gèrent la relation
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#  4. Modifier un produit
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminUser])
def modifier_produit(request, produit_id):
    try:
        produit = Produit.objects.get(pk=produit_id)
    except Produit.DoesNotExist:
        return Response({"error": "Produit non trouvé"}, status=status.HTTP_404_NOT_FOUND)

    serializer = ProduitSerialized(produit, data=request.data, partial=True, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#  5. Supprimer un produit
@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def supprimer_produit(request, produit_id):
    try:
        produit = Produit.objects.get(pk=produit_id)
    except Produit.DoesNotExist:
        return Response({"error": "Produit non trouvé"}, status=status.HTTP_404_NOT_FOUND)

    produit.delete()
    return Response({"message": "Produit supprimé avec succès"}, status=status.HTTP_204_NO_CONTENT)


#  6. Produits par catégorie
@api_view(['GET'])
@permission_classes([AllowAny])
def produits_par_categorie(request, categorieNom):
    try:
        categorie = Categorie.objects.get(nom=categorieNom)
    except Categorie.DoesNotExist:
        return Response({"error": "Catégorie non trouvée"}, status=status.HTTP_404_NOT_FOUND)

    return repondre(request, produits_visibles(request).filter(categorie=categorie).order_by("?"))


# produit par grosse categorie
@api_view(['GET'])
@permission_classes([AllowAny])
def produitpargroscategorie(request, gros_categorie):
    produits = produits_visibles(request).filter(categorie__gros_categorie=gros_categorie).order_by("?")
    return repondre(request, produits)


# 7. Produits par sous-catégorie
@api_view(['GET'])
@permission_classes([AllowAny])
def produits_par_souscategorie(request, souscategorie_id):
    try:
        souscategorie = SubCategorie.objects.get(pk=souscategorie_id)
    except SubCategorie.DoesNotExist:
        return Response({"error": "Sous-catégorie non trouvée"}, status=status.HTTP_404_NOT_FOUND)

    return repondre(request, produits_visibles(request).filter(sous_categorie=souscategorie).order_by("nom"))


# 8. Produits par étiquette
@api_view(['GET'])
@permission_classes([AllowAny])
def produits_par_etiquette(request, etiquette_id):
    try:
        etiquette = Etiquette.objects.get(pk=etiquette_id)
    except Etiquette.DoesNotExist:
        return Response({"error": "Étiquette non trouvée"}, status=status.HTTP_404_NOT_FOUND)

    return repondre(request, produits_visibles(request).filter(etiquette=etiquette).order_by("nom"))


@api_view(['GET'])
@permission_classes([AllowAny])
def QuatresPremiers(request, gros_categorie):
    produits = produits_visibles(request).filter(categorie__gros_categorie=gros_categorie).order_by('id')[:5]
    return repondre(request, produits)


@api_view(['GET'])
@permission_classes([AllowAny])
def produitRecents(request):
    return repondre(request, produits_visibles(request).order_by('-created_at')[:4])


@api_view(['GET'])
@permission_classes([AllowAny])
def quatre_produit_gros_oeuvres(request, gros_categorie):
    produits = produits_visibles(request).filter(categorie__gros_categorie=gros_categorie).order_by("?")[:4]
    return repondre(request, produits)


@api_view(['GET'])
@permission_classes([AllowAny])
def venteHebdo(request):
    return repondre(request, produits_visibles(request).order_by("?")[:4])


@api_view(['GET'])
@permission_classes([AllowAny])
def recuperer_deux_dernier_produit(request):
    return repondre(request, produits_visibles(request).order_by("-created_at")[:2])


@api_view(['GET'])
@permission_classes([AllowAny])
def Produit_par_gros_categorie(request, gros_categorie):
    return repondre(request, produits_visibles(request).filter(categorie__gros_categorie=gros_categorie))
