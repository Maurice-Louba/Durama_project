"""Logique métier partagée par les vues (commandes, stock)."""
from django.db import transaction
from django.db.models import F
from rest_framework import status
from rest_framework.exceptions import APIException

from .models import Commande, CommandeItem, ContenuPanier, Panier, Produit, ProduitVariable


class ErreurCommande(APIException):
    """Erreur métier renvoyée telle quelle au client : {"message": "..."} (format plat)."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Commande impossible."

    def __init__(self, message, status_code=None):
        super().__init__({'message': message})
        if status_code:
            self.status_code = status_code


def _retirer_du_stock(item):
    """Décrémente le stock de façon atomique (pas de survente si deux clients commandent en même temps)."""
    produit = item.produit
    if produit.etat_stock == 'sur commande':
        return
    if produit.etat_stock == 'rupture stock':
        raise ErreurCommande(f"« {produit.nom} » est en rupture de stock.")

    if item.produit_variable_id:
        ok = ProduitVariable.objects.filter(pk=item.produit_variable_id, quantite__gte=item.quantite) \
            .update(quantite=F('quantite') - item.quantite)
    else:
        ok = Produit.objects.filter(pk=produit.pk, quantite__gte=item.quantite) \
            .update(quantite=F('quantite') - item.quantite)
        Produit.objects.filter(pk=produit.pk, quantite=0).update(etat_stock='rupture stock')
    if not ok:
        raise ErreurCommande(f"Stock insuffisant pour « {produit.nom} ».")


def _remettre_en_stock(item):
    if item.produit.etat_stock == 'sur commande':
        return
    if item.produit_variable_id:
        ProduitVariable.objects.filter(pk=item.produit_variable_id).update(quantite=F('quantite') + item.quantite)
    else:
        Produit.objects.filter(pk=item.produit_id).update(quantite=F('quantite') + item.quantite)
        Produit.objects.filter(pk=item.produit_id, etat_stock='rupture stock', quantite__gt=0).update(etat_stock='en stock')


@transaction.atomic
def passer_commande(user, infos=None):
    """
    Transforme le panier actif en commande : copie des lignes au prix actuel, contrôle et
    décrément du stock, puis fermeture du panier. Tout est annulé si une étape échoue.
    """
    infos = infos or {}
    panier = Panier.objects.filter(user=user, actif=True).first()
    if panier is None:
        raise ErreurCommande('Aucun panier actif', status.HTTP_404_NOT_FOUND)

    items = list(ContenuPanier.objects.filter(panier=panier)
                 .select_related('produit', 'produit_variable').prefetch_related('attributs'))
    if not items:
        raise ErreurCommande('Votre panier est vide')

    commande = Commande.objects.create(user=user, panier=panier, **infos)

    for item in items:
        if not item.produit.est_publie:
            raise ErreurCommande(f"« {item.produit.nom} » n'est plus disponible.")
        prix = item.prix_unitaire
        if prix is None:
            raise ErreurCommande(f"« {item.produit.nom} » n'a pas de prix.")
        _retirer_du_stock(item)
        ligne = CommandeItem.objects.create(
            commande=commande,
            produit=item.produit,
            produit_variable=item.produit_variable,
            quantite=item.quantite,
            prix_unitaire=prix,
        )
        ligne.attributs.set(item.attributs.all())
        Produit.objects.filter(pk=item.produit_id).update(nombres_ventes=F('nombres_ventes') + item.quantite)

    commande.calculer_totaux()

    panier.actif = False
    panier.save(update_fields=['actif', 'updated_at'])
    return commande


@transaction.atomic
def annuler_commande(commande):
    """Annule une commande et remet les produits en stock (une seule fois)."""
    if commande.statut == 'annulee':
        return commande
    for item in commande.items.select_related('produit'):
        _remettre_en_stock(item)
        Produit.objects.filter(pk=item.produit_id, nombres_ventes__gte=item.quantite) \
            .update(nombres_ventes=F('nombres_ventes') - item.quantite)
    commande.statut = 'annulee'
    commande.save(update_fields=['statut', 'updated_at'])
    return commande
