from decimal import Decimal

from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import MateriauDevis, ProjetDevis, Produit
from ..serializer import ProjetDevisSerializer

# Valeurs utilisées quand le frontend n'envoie pas le champ (comportement historique)
VALEURS_PAR_DEFAUT = {
    "type_projet": "maison",
    "nombre_etages": 1,
    "structure": "beton",
    "type_sol": "inconnu",
    "finition": "moyen",
    "toiture": "tuile",
    "objectif": "construction",
    "options": [],
}
SURFACE_MAX = 100000  # m² par étage


def generer_devis(data, user):
    """Génère un devis pour un utilisateur"""
    with transaction.atomic():
        # ==============================
        # 1. Création projet
        # ==============================
        projet = ProjetDevis.objects.create(user=user, **data)

        # ==============================
        # 2. Surface totale
        # ==============================
        surface_totale = Decimal(str(projet.surface)) * projet.nombre_etages

        # ==============================
        # 3. Ratios matériaux (TOUS en Decimal)
        # ==============================
        ratios = {
            "basique": {"beton": Decimal('0.18'), "acier": Decimal('30'), "briques": Decimal('9'), 
                       "sable": Decimal('0.45'), "gravier": Decimal('0.65')},
            "moyen": {"beton": Decimal('0.2'), "acier": Decimal('35'), "briques": Decimal('10'), 
                     "sable": Decimal('0.5'), "gravier": Decimal('0.7')},
            "haut": {"beton": Decimal('0.25'), "acier": Decimal('45'), "briques": Decimal('12'), 
                    "sable": Decimal('0.6'), "gravier": Decimal('0.8')},
        }
        
        finition_key = projet.finition if projet.finition in ratios else "moyen"
        ratio = ratios.get(finition_key, ratios["moyen"])

        beton = surface_totale * ratio["beton"]
        acier = surface_totale * ratio["acier"]
        briques = surface_totale * ratio["briques"]
        sable = surface_totale * ratio["sable"]
        gravier = surface_totale * ratio["gravier"]

        total = Decimal('0')
        materiaux_response = []

        # ==============================
        # 4. Liste des matériaux (TOUTES les quantités en Decimal)
        # ==============================
        liste = [
            {"nom": "Ciment", "quantite": beton * Decimal('7'), "unite": "sacs"},
            {"nom": "Sable", "quantite": sable * Decimal('1000'), "unite": "kg"},
            {"nom": "Gravier", "quantite": gravier * Decimal('1000'), "unite": "kg"},
            {"nom": "Fer à béton", "quantite": acier, "unite": "kg"},
            {"nom": "Briques", "quantite": briques, "unite": "unités"},
            {"nom": "Bois coffrage", "quantite": surface_totale * Decimal('2'), "unite": "m³"},
            {"nom": "Poutres béton", "quantite": surface_totale * Decimal('0.5'), "unite": "unités"},
            {"nom": "Tuiles", "quantite": surface_totale * Decimal('1.2'), "unite": "unités"},
            {"nom": "Charpente bois", "quantite": surface_totale * Decimal('0.3'), "unite": "m³"},
            {"nom": "Membrane étanchéité", "quantite": surface_totale, "unite": "m²"},
            {"nom": "Portes", "quantite": projet.nombre_etages * Decimal('10'), "unite": "unités"},
            {"nom": "Fenêtres", "quantite": projet.nombre_etages * Decimal('15'), "unite": "unités"},
            {"nom": "Vitrage", "quantite": projet.nombre_etages * Decimal('20'), "unite": "m²"},
        ]

        if "electricite" in projet.options:
            liste.extend([
                {"nom": "Câbles électriques", "quantite": surface_totale * Decimal('5'), "unite": "m"},
                {"nom": "Interrupteurs et prises", "quantite": projet.nombre_etages * Decimal('20'), "unite": "unités"},
                {"nom": "Disjoncteurs", "quantite": projet.nombre_etages * Decimal('5'), "unite": "unités"},
            ])

        if "plomberie" in projet.options:
            liste.extend([
                {"nom": "Tuyaux PVC", "quantite": surface_totale * Decimal('3'), "unite": "m"},
                {"nom": "Raccords plomberie", "quantite": projet.nombre_etages * Decimal('15'), "unite": "unités"},
                {"nom": "Robinetterie", "quantite": projet.nombre_etages * Decimal('10'), "unite": "unités"},
            ])

        if "peinture" in projet.options:
            liste.append({"nom": "Peinture", "quantite": surface_totale * Decimal('0.2'), "unite": "litres"})
            liste.append({"nom": "Enduit", "quantite": surface_totale * Decimal('0.1'), "unite": "kg"})

        # ==============================
        # 5. Calcul des prix
        # ==============================
        def get_prix_produit(nom):
            produit = Produit.objects.filter(nom__icontains=nom, est_publie=True, prix_vente__isnull=False).first()
            if produit:
                return produit, Decimal(produit.prix_effectif)
            
            prix_marche = {
                "Ciment": Decimal('75'), "Sable": Decimal('0.5'), "Gravier": Decimal('0.7'),
                "Fer à béton": Decimal('6'), "Briques": Decimal('1.5'), "Bois coffrage": Decimal('300'),
                "Poutres béton": Decimal('500'), "Tuiles": Decimal('15'), "Charpente bois": Decimal('400'),
                "Membrane étanchéité": Decimal('50'), "Portes": Decimal('400'), "Fenêtres": Decimal('250'),
                "Vitrage": Decimal('100'), "Câbles électriques": Decimal('10'), "Interrupteurs et prises": Decimal('15'),
                "Disjoncteurs": Decimal('50'), "Tuyaux PVC": Decimal('12'), "Raccords plomberie": Decimal('5'),
                "Robinetterie": Decimal('200'), "Peinture": Decimal('25'), "Enduit": Decimal('5'),
            }
            return None, prix_marche.get(nom, Decimal('0'))

        for item in liste:
            produit, prix_unitaire = get_prix_produit(item["nom"])
            quantite = item["quantite"]  # Déjà en Decimal
            prix_total = prix_unitaire * quantite
            total += prix_total

            MateriauDevis.objects.create(
                projet=projet,
                produit=produit,
                nom=item["nom"],
                quantite=float(quantite),  # Convertir en float pour la BD
                unite=item["unite"],
                prix_unitaire=prix_unitaire.quantize(Decimal('0.01')),
                prix_total=prix_total.quantize(Decimal('0.01'))
            )

            materiaux_response.append({
                "id": len(materiaux_response) + 1,
                "nom": item["nom"],
                "quantite": float(quantite),
                "unite": item["unite"],
                "produit_nom": item["nom"],
                "prix_unitaire": float(prix_unitaire),
                "prix_total": float(prix_total)
            })

        # ==============================
        # 6. Frais supplémentaires (TOUS en Decimal)
        # ==============================
        main_oeuvre = total * Decimal('0.3')
        imprevus = total * Decimal('0.1')
        total_general = total + main_oeuvre + imprevus

        projet.prix_estime = total_general.quantize(Decimal('0.01'))
        projet.save(update_fields=['prix_estime', 'updated_at'])

        return {
            "projet_id": projet.id,
            "surface_totale": float(surface_totale),
            "materiaux": materiaux_response,
            "prix_total": float(total_general)
        }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generer_devis_view(request):
    """Vue pour générer un devis"""
    if not request.data.get('ville'):
        return Response({"error": "Le champ 'ville' est obligatoire"}, status=400)
    if not request.data.get('surface'):
        return Response({"error": "Le champ 'surface' est obligatoire"}, status=400)

    donnees = {**VALEURS_PAR_DEFAUT, **{k: v for k, v in request.data.items() if v not in (None, '')}}
    serializer = ProjetDevisSerializer(data=donnees, context={'request': request})
    if not serializer.is_valid():
        return Response({"error": "Données invalides", "errors": serializer.errors}, status=400)
    if serializer.validated_data['surface'] > SURFACE_MAX:
        return Response({"error": f"La surface ne peut pas dépasser {SURFACE_MAX} m²"}, status=400)

    # Générer le devis
    result = generer_devis(serializer.validated_data, request.user)

    projet = ProjetDevis.objects.prefetch_related('materiaux__produit').get(id=result['projet_id'])
    response_data = ProjetDevisSerializer(projet, context={'request': request}).data
    response_data['materiaux'] = result['materiaux']
    return Response(response_data, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dernier_devis_view(request):
    """Récupérer le dernier devis"""
    dernier = ProjetDevis.objects.filter(user=request.user).prefetch_related('materiaux__produit')         .order_by('-created_at').first()
    if not dernier:
        return Response({"message": "Aucun devis"}, status=404)
    return Response(ProjetDevisSerializer(dernier, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tous_les_devis_view(request):
    """Récupérer tous les devis"""
    projets = ProjetDevis.objects.filter(user=request.user).prefetch_related('materiaux__produit')         .order_by('-created_at')
    return Response(ProjetDevisSerializer(projets, many=True, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_devis_detail(request, devis_id):
    """Récupérer un devis spécifique avec ses matériaux (avant : paramètre mal nommé, plantait toujours)"""
    devis = ProjetDevis.objects.prefetch_related('materiaux__produit').filter(id=devis_id, user=request.user).first()
    if devis is None:
        return Response({"error": "Devis non trouvé"}, status=404)
    return Response(ProjetDevisSerializer(devis, context={'request': request}).data, status=200)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_devis(request, devis_id):
    """Supprimer un devis (les matériaux sont supprimés en cascade)"""
    supprimes, _ = ProjetDevis.objects.filter(id=devis_id, user=request.user).delete()
    if not supprimes:
        return Response({"error": "Devis non trouvé"}, status=404)
    return Response({"message": "Devis supprimé avec succès"}, status=200)
