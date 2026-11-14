import json
from decimal import Decimal

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import ContenuPanier, Panier
from ..serializer import PanierItemSerialized

QUANTITE_MAX_PAR_ARTICLE = 10000


def _items(panier):
    return ContenuPanier.objects.filter(panier=panier).select_related(
        'panier__user', 'produit_variable__produit',
        'produit__vendeur', 'produit__categorie', 'produit__sous_categorie__categorie_principale', 'produit__etiquette',
    ).prefetch_related('attributs__typeAttribut')


def _item_du_client(request, pk):
    """Un article du panier ACTIF de l'utilisateur connecté (jamais celui d'un autre client)."""
    panier = Panier.panier_actif(request.user)
    return ContenuPanier.objects.filter(pk=pk, panier=panier).first()


def _lire_attributs_ids(valeur):
    """Accepte une liste, ou une chaîne JSON « [1, 2] » (envoi en FormData)."""
    if valeur in (None, ''):
        return []
    if isinstance(valeur, str):
        try:
            valeur = json.loads(valeur)
        except json.JSONDecodeError:
            valeur = [v for v in valeur.strip('[]').split(',') if v.strip()]
    if not isinstance(valeur, (list, tuple)):
        valeur = [valeur]
    return list(valeur)


def _donnees_item(request, attributs_ids):
    data = {}
    for champ in ('produit_id', 'produit_variable_id', 'quantite'):
        if champ in request.data:
            data[champ] = request.data.get(champ)
    if attributs_ids is not None:
        data['attributs_ids'] = attributs_ids
    if data.get('produit_variable_id') in ('', 'null', None):
        data.pop('produit_variable_id', None)
    return data


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def panier_items(request):
    """
    - GET  : Récupérer tous les items du panier actif de l'utilisateur connecté
    - POST : Ajouter un produit dans le panier actif
    """
    panier = Panier.panier_actif(request.user)

    if request.method == 'GET':
        serializer = PanierItemSerialized(_items(panier), many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 1. Validation complète (produit existant, publié, en stock, quantité >= 1, variante cohérente...)
    data = _donnees_item(request, _lire_attributs_ids(request.data.get('attributs_ids')))
    serializer = PanierItemSerialized(data=data, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    valide = serializer.validated_data
    produit = valide['produit']
    variante = valide.get('produit_variable')
    quantite = valide['quantite']
    attributs_ids_set = set(valide.get('attributs_ids') or [])

    with transaction.atomic():
        # 2. Même produit + même variante + mêmes attributs déjà dans le panier ? -> on cumule
        existants = ContenuPanier.objects.filter(panier=panier, produit=produit,
                                                 produit_variable=variante).prefetch_related('attributs')
        item_existant = next(
            (item for item in existants if {a.id for a in item.attributs.all()} == attributs_ids_set),
            None,
        )

        if item_existant:
            nouvelle_quantite = item_existant.quantite + quantite
            if nouvelle_quantite > QUANTITE_MAX_PAR_ARTICLE:
                return Response({'quantite': [f"Quantité maximale : {QUANTITE_MAX_PAR_ARTICLE}."]},
                                status=status.HTTP_400_BAD_REQUEST)
            item_existant.quantite = nouvelle_quantite
            item_existant.save(update_fields=['quantite', 'updated_at'])
            item = _items(panier).get(id=item_existant.id)
            return Response(PanierItemSerialized(item, context={'request': request}).data, status=status.HTTP_200_OK)

        # 3. Sinon création
        item = serializer.save(panier=panier)

    item = _items(panier).get(id=item.id)
    return Response(PanierItemSerialized(item, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deuxElementsDuPanier(request):
    panier = Panier.panier_actif(request.user)
    contenu = _items(panier).order_by('-created_at')[:2]
    serializer = PanierItemSerialized(contenu, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def panier_item_detail(request, pk):
    item = _item_du_client(request, pk)
    if item is None:
        return Response(
            {"error": "Item non trouvé dans le panier actif"},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        item = _items(item.panier).get(id=item.id)
        return Response(PanierItemSerialized(item, context={'request': request}).data, status=status.HTTP_200_OK)

    if request.method in ['PUT', 'PATCH']:
        attributs_ids = _lire_attributs_ids(request.data.get('attributs_ids')) if 'attributs_ids' in request.data else None
        serializer = PanierItemSerialized(
            item,
            data=_donnees_item(request, attributs_ids),
            partial=True,  # on ne change jamais le panier, et PUT sans produit_id ne doit pas échouer
            context={'request': request}
        )
        if serializer.is_valid():
            updated_item = serializer.save()
            updated_item = _items(item.panier).get(id=updated_item.id)
            return Response(PanierItemSerialized(updated_item, context={'request': request}).data,
                            status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    item.delete()
    return Response(
        {"message": "Item supprimé du panier"},
        status=status.HTTP_204_NO_CONTENT
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def total_panier(request):
    """
    Total au prix réellement facturé (promo valide, prix de la variante...) :
    c'est le même calcul que celui utilisé lors de la commande.
    """
    panier = Panier.panier_actif(request.user)
    total = Decimal('0')
    for item in _items(panier):
        total += (item.prix_unitaire or Decimal('0')) * item.quantite
    return Response(total, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def augmenter_quantite(request, pk):
    item = _item_du_client(request, pk)
    if item is None:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if item.quantite >= QUANTITE_MAX_PAR_ARTICLE:
        return Response({"error": f"Quantité maximale : {QUANTITE_MAX_PAR_ARTICLE}."}, status=status.HTTP_400_BAD_REQUEST)
    item.quantite += 1
    item.save(update_fields=['quantite', 'updated_at'])
    return Response({"message": "Quantité mise à jour avec succès ✅"})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dimunuer_quantite(request, pk):
    item = _item_du_client(request, pk)
    if item is None:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if item.quantite > 1:
        item.quantite -= 1
        item.save(update_fields=['quantite', 'updated_at'])
    return Response({"message": "Quantité mise à jour avec succès ✅"})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def supprimer_item(request, pk):
    item = _item_du_client(request, pk)
    if item is None:
        return Response(status=status.HTTP_404_NOT_FOUND)
    item.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def vider_panier(request):
    panier = Panier.panier_actif(request.user)
    items = ContenuPanier.objects.filter(panier=panier)

    if not items.exists():
        return Response({"message": "Le panier est déjà vide 🧺"}, status=status.HTTP_200_OK)
    items.delete()
    return Response({"message": "Le panier a été vidé avec succès 🧹"}, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nombre_element_panier(request):
    panier = Panier.objects.filter(user=request.user, actif=True).first()
    if panier is None:
        return Response(0)
    return Response(ContenuPanier.objects.filter(panier=panier).count())
