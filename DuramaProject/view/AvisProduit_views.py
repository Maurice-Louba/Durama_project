from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ..models import AvisProduit, Produit
from ..serializer import AvisProduitSerialized


def _avis():
    return AvisProduit.objects.select_related(
        'user', 'produit__vendeur', 'produit__categorie',
        'produit__sous_categorie__categorie_principale', 'produit__etiquette',
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tousAvis(request):
    avis = _avis().order_by('-created_at')
    avisSerial = AvisProduitSerialized(avis, many=True, context={'request': request})
    return Response(avisSerial.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def AvisSurUnProduit(request, produit_id):
    avis_produit = _avis().filter(produit_id=produit_id).order_by('-created_at')
    avis_produitSeria = AvisProduitSerialized(avis_produit, many=True, context={'request': request})
    return Response(avis_produitSeria.data)


@swagger_auto_schema(
    method='post',
    request_body=AvisProduitSerialized,
    responses={
        201: AvisProduitSerialized,
        400: 'Bad Request'
    }
)
# NB : @api_view doit être placé AU-DESSUS de @permission_classes, sinon la permission
# est ignorée (c'était le cas avant : un visiteur anonyme provoquait une erreur 500).
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def faireAvis(request, produit_id):
    try:
        produit = Produit.objects.get(pk=produit_id, est_publie=True)
    except Produit.DoesNotExist:
        return Response({'error': 'Produit introuvable'}, status=status.HTTP_404_NOT_FOUND)

    serializer = AvisProduitSerialized(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save(produit=produit)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def modifierAvisProduit(request, produit_id):
    """Modifie l'avis de l'utilisateur connecté sur ce produit."""
    avis = AvisProduit.objects.filter(produit_id=produit_id, user=request.user).order_by('-created_at').first()
    if avis is None:
        return Response({'error': 'avis non trouvé'}, status=status.HTTP_404_NOT_FOUND)

    serializer = AvisProduitSerialized(avis, data=request.data, context={'request': request},
                                       partial=(request.method == 'PATCH'))
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def deleteAvisProduit(request, produit_id):
    """
    Supprime l'avis de l'utilisateur connecté sur ce produit.
    (Avant : la vue essayait de supprimer des PRODUITS au lieu de l'avis.)
    """
    avis = AvisProduit.objects.filter(produit_id=produit_id, user=request.user)
    if not avis.exists():
        return Response({'error': 'avis non trouvé'}, status=status.HTTP_404_NOT_FOUND)
    avis.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([AllowAny])
def detailAvisSurProduit(request, produit_id):
    """
    Détail d'un avis. L'URL s'appelle <produit_id> mais il s'agit de l'id de l'avis
    (avant : la signature attendait `pk` et la vue plantait à chaque appel).
    """
    try:
        avis = _avis().get(pk=produit_id)
    except AvisProduit.DoesNotExist:
        return Response({'error': 'avis non trouvé'}, status=status.HTTP_404_NOT_FOUND)
    avisSerializ = AvisProduitSerialized(avis, context={'request': request})
    return Response(avisSerializ.data)
