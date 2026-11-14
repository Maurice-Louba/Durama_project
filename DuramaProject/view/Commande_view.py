from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Commande
from ..serializer import CommandeSerialized, CommandeStatutSerialized
from ..services import annuler_commande, passer_commande

# Champs que le client peut renseigner en passant commande (tous optionnels)
CHAMPS_CLIENT = ('adresse_livraison', 'notes', 'latitude', 'longitude')


def _commandes():
    return Commande.objects.select_related('user', 'panier__user').prefetch_related(
        'items__produit', 'items__attributs__typeAttribut'
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def faire_une_commande(request):
    infos = CommandeSerialized(data={k: request.data[k] for k in CHAMPS_CLIENT if k in request.data},
                               partial=True, context={'request': request})
    infos.is_valid(raise_exception=True)

    # Copie du panier, contrôle/décrément du stock et fermeture du panier en une seule transaction
    commande = passer_commande(request.user, dict(infos.validated_data))
    commande = _commandes().get(pk=commande.pk)
    return Response(CommandeSerialized(commande, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tous_les_commandes(request):
    # Le staff voit toutes les commandes ; un client ne voit que les siennes
    commandes = _commandes().order_by('-created_at')
    if not request.user.is_staff:
        commandes = commandes.filter(user=request.user)
    statut = request.query_params.get('statut')
    if statut:
        commandes = commandes.filter(statut=statut)
    commandesSerial = CommandeSerialized(commandes, many=True, context={'request': request})
    return Response(commandesSerial.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def commandeParUser(request, user_id):
    if not request.user.is_staff and request.user.id != user_id:
        return Response({'message': "Vous n'avez pas accès aux commandes de cet utilisateur"},
                        status=status.HTTP_403_FORBIDDEN)
    commandes = _commandes().filter(user_id=user_id).order_by('-created_at')
    commandesSeria = CommandeSerialized(commandes, many=True, context={'request': request})
    return Response(commandesSeria.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def changerUneCommande(request, pk):
    """
    - Staff : change le statut (selon les transitions autorisées) et/ou les frais de livraison.
    - Client : tant que la commande est « en attente », peut modifier adresse/notes ou l'annuler
      (en envoyant {"statut": "annulee"}).
    """
    try:
        commande = Commande.objects.get(pk=pk)
    except Commande.DoesNotExist:
        return Response({'error': 'commande inexistante'}, status=status.HTTP_404_NOT_FOUND)

    if not request.user.is_staff and commande.user_id != request.user.id:
        return Response({'error': 'commande inexistante'}, status=status.HTTP_404_NOT_FOUND)

    nouveau_statut = request.data.get('statut')

    if request.user.is_staff:
        serializer = CommandeStatutSerialized(commande, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            if nouveau_statut == 'annulee':
                annuler_commande(commande)
                serializer.validated_data.pop('statut', None)
            serializer.save()
    else:
        if commande.statut != 'en_attente':
            return Response({'error': "La commande ne peut plus être modifiée (déjà prise en charge)"},
                            status=status.HTTP_400_BAD_REQUEST)
        if nouveau_statut not in (None, '', 'annulee'):
            return Response({'error': "Vous pouvez seulement annuler votre commande"},
                            status=status.HTTP_403_FORBIDDEN)
        serializer = CommandeSerialized(commande, data={k: request.data[k] for k in CHAMPS_CLIENT if k in request.data},
                                        partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save()
            if nouveau_statut == 'annulee':
                annuler_commande(commande)

    commande = _commandes().get(pk=pk)
    return Response(CommandeSerialized(commande, context={'request': request}).data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nombre_commande(request):
    return Response(Commande.objects.filter(user=request.user).count())
