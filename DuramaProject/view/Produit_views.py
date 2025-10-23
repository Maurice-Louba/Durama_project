from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ..models import Produit, Categorie, SubCategorie, Etiquette
from ..serializer import ProduitSerialized


#  1. Liste de tous les produits (option tri / recherche simple)
@api_view(['GET'])
@permission_classes([AllowAny])
def liste_produits(request):
    produits = Produit.objects.all().order_by("nom")
    serializer = ProduitSerialized(produits, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def TousLesProduitsAleatoirement(request):
    try:
        # Récupération aléatoire des produits
        produits = Produit.objects.all().order_by('?')  
        produits_serialized = ProduitSerialized(produits, many=True)
        return Response(produits_serialized.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#  2. Détail d’un produit
@api_view(['GET'])
@permission_classes([AllowAny])
def detail_produit(request, produit_id):
    try:
        produit = Produit.objects.get(pk=produit_id)
        produit.increment_views()  # On incrémente le compteur de vues à chaque affichage
    except Produit.DoesNotExist:
        return Response({"error": "Produit non trouvé"}, status=status.HTTP_404_NOT_FOUND)

    serializer = ProduitSerialized(produit)
    return Response(serializer.data, status=status.HTTP_200_OK)


#  3. Créer un produit
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def creer_produit(request):
    serializer = ProduitSerialized(data=request.data)
    if serializer.is_valid():
        serializer.save()  # Les champs categorie_id, sous_categorie_id et etiquette_id gèrent la relation
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#  4. Modifier un produit
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def modifier_produit(request, produit_id):
    try:
        produit = Produit.objects.get(pk=produit_id)
    except Produit.DoesNotExist:
        return Response({"error": "Produit non trouvé"}, status=status.HTTP_404_NOT_FOUND)

    serializer = ProduitSerialized(produit, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#  5. Supprimer un produit
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
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
def produits_par_categorie(request, categorie_id):
    try:
        categorie = Categorie.objects.get(pk=categorie_id)
    except Categorie.DoesNotExist:
        return Response({"error": "Catégorie non trouvée"}, status=status.HTTP_404_NOT_FOUND)

    produits = Produit.objects.filter(categorie=categorie).order_by("nom")
    serializer = ProduitSerialized(produits, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

# produit par grosse categorie
@api_view(['GET'])
@permission_classes([AllowAny])
def produitpargroscategorie(request,gros_categorie):
    try:
        categorie=Categorie.objects.filter(gros_categorie=gros_categorie)
    except Categorie.DoesNotExist:
        return Response({"message":"categories non existantes"},status=status.HTTP_404_NOT_FOUND)
    produit=Produit.objects.filter(categorie__in=categorie)
    serializer=ProduitSerialized(produit,many=True)
    return Response(serializer.data)


# 7. Produits par sous-catégorie
@api_view(['GET'])
@permission_classes([AllowAny])
def produits_par_souscategorie(request, souscategorie_id):
    try:
        souscategorie = SubCategorie.objects.get(pk=souscategorie_id)
    except SubCategorie.DoesNotExist:
        return Response({"error": "Sous-catégorie non trouvée"}, status=status.HTTP_404_NOT_FOUND)

    produits = Produit.objects.filter(sous_categorie=souscategorie).order_by("nom")
    serializer = ProduitSerialized(produits, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# 8. Produits par étiquette
@api_view(['GET'])
@permission_classes([AllowAny])
def produits_par_etiquette(request, etiquette_id):
    try:
        etiquette = Etiquette.objects.get(pk=etiquette_id)
    except Etiquette.DoesNotExist:
        return Response({"error": "Étiquette non trouvée"}, status=status.HTTP_404_NOT_FOUND)

    produits = Produit.objects.filter(etiquette=etiquette).order_by("nom")
    serializer = ProduitSerialized(produits, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def QuatresPremiers(request,gros_categorie):
    try:
        categorie=Categorie.objects.filter(gros_categorie=gros_categorie)
    except Categorie.DoesNotExist:
        return Response({'message':"Categorie non trouvé"},status=status.HTTP_404_NOT_FOUND)
    produit=Produit.objects.filter(categorie__in=categorie)[:5]
    produitSerial=ProduitSerialized(produit,many=True)
    return Response(produitSerial.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def produitRecents(request):
    try:
        produits=Produit.objects.filter().order_by('-created_at')[:4]
    except Produit.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    produitSeriali=ProduitSerialized(produits,many=True)
    return Response(produitSeriali.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def quatre_produit_gros_oeuvres(request,gros_categorie):
    try:
        categorie=Categorie.objects.filter(gros_categorie=gros_categorie)
    except Categorie.DoesNotExist:
        return Response(status=status.HTTP_204_NO_CONTENT)
    produits=Produit.objects.filter(categorie__in=categorie).order_by("?")[:4]
    produitsSeria=ProduitSerialized(produits,many=True)
    return Response(produitsSeria.data)