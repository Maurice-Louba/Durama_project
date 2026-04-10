from decimal import Decimal
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view,permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from ..models import ProjetDevis, Produit, MateriauDevis
from ..serializer import ProjetDevisSerializer
from rest_framework.permissions import AllowAny,IsAuthenticated

def get_user_from_request(request):
    """Récupérer l'utilisateur depuis le token JWT"""
    auth = JWTAuthentication()
    try:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header:
            return None
        
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None
        
        token = parts[1]
        validated_token = auth.get_validated_token(token)
        user = auth.get_user(validated_token)
        return user
    except Exception as e:
        print(f"Erreur d'authentification: {e}")
        return None

def generer_devis(data, user):
    """Génère un devis pour un utilisateur"""
    with transaction.atomic():
        # ==============================
        # 1. Création projet
        # ==============================
        projet = ProjetDevis.objects.create(
            user=user,
            nom_projet=data.get("nom_projet", ""),
            ville=data.get("ville", ""),
            quartier=data.get("quartier", ""),
            type_projet=data.get("type_projet", "maison"),
            surface=Decimal(str(data.get("surface", 0))),
            nombre_etages=int(data.get("nombre_etages", 1)),
            structure=data.get("structure", "beton"),
            type_sol=data.get("type_sol", "inconnu"),
            finition=data.get("finition", "moyen"),
            toiture=data.get("toiture", "tuile"),
            options=data.get("options", []),
            budget=Decimal(str(data.get("budget", 0))) if data.get("budget") else None,
            objectif=data.get("objectif", "construction")
        )

        # ==============================
        # 2. Surface totale
        # ==============================
        surface_totale = projet.surface * projet.nombre_etages

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
            produit = Produit.objects.filter(nom__icontains=nom).first()
            if produit:
                return produit, Decimal(str(produit.prix_vente))
            
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
                prix_unitaire=prix_unitaire,
                prix_total=prix_total
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

        projet.prix_estime = total_general
        projet.save()

        return {
            "projet_id": projet.id,
            "surface_totale": float(surface_totale),
            "materiaux": materiaux_response,
            "prix_total": float(total_general)
        }


@csrf_exempt
@api_view(['POST'])
def generer_devis_view(request):
    """Vue pour générer un devis"""
    try:
        print("=" * 50)
        print("DONNÉES REÇUES:", request.data)
        print("=" * 50)
        
        # Récupérer l'utilisateur
        user = get_user_from_request(request)
        
        if not user:
            return Response(
                {"error": "Utilisateur non authentifié"}, 
                status=401
            )
        
        # Vérifier les champs obligatoires
        if not request.data.get('ville'):
            return Response({"error": "Le champ 'ville' est obligatoire"}, status=400)
        
        if not request.data.get('surface'):
            return Response({"error": "Le champ 'surface' est obligatoire"}, status=400)
        
        # Générer le devis
        result = generer_devis(request.data, user)
        
        # Récupérer le projet
        projet = ProjetDevis.objects.get(id=result['projet_id'])
        
        # Sérialiser la réponse
        serializer = ProjetDevisSerializer(projet)
        response_data = serializer.data
        response_data['materiaux'] = result['materiaux']
        
        return Response(response_data, status=201)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({"error": str(e)}, status=400)


@csrf_exempt
@api_view(['GET'])
def dernier_devis_view(request):
    """Récupérer le dernier devis"""
    try:
        user = get_user_from_request(request)
        if not user:
            return Response({"error": "Non authentifié"}, status=401)
        
        dernier = ProjetDevis.objects.filter(user=user).order_by('-created_at').first()
        if not dernier:
            return Response({"message": "Aucun devis"}, status=404)
        
        serializer = ProjetDevisSerializer(dernier)
        return Response(serializer.data)
        
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@csrf_exempt
@api_view(['GET'])
def tous_les_devis_view(request):
    """Récupérer tous les devis"""
    try:
        user = get_user_from_request(request)
        if not user:
            return Response({"error": "Non authentifié"}, status=401)
        
        projets = ProjetDevis.objects.filter(user=user).order_by('-created_at')
        serializer = ProjetDevisSerializer(projets, many=True)
        return Response(serializer.data)
        
    except Exception as e:
        return Response({"error": str(e)}, status=400)



@csrf_exempt
@api_view(['GET'])
def get_devis_detail(request, devis_idd):
    """Récupérer un devis spécifique avec ses matériaux"""
    try:
        # Récupérer l'utilisateur depuis le token JWT
        user = get_user_from_request(request)
        
        if not user:
            return Response(
                {"error": "Utilisateur non authentifié"}, 
                status=401
            )
        
        # Récupérer le devis avec ses matériaux (prefetch_related optimise la requête)
        devis = ProjetDevis.objects.prefetch_related('materiaux').get(id=devis_id, user=user)
        
        # Sérialiser avec le serializer qui inclut les matériaux
        serializer = ProjetDevisSerializer(devis)
        
        return Response(serializer.data, status=200)
        
    except ProjetDevis.DoesNotExist:
        return Response(
            {"error": "Devis non trouvé"}, 
            status=404
        )
    except Exception as e:
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": str(e)}, 
            status=400
        )



@csrf_exempt
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_devis(request, devis_id):
    """Supprimer un devis"""
    try:
        # Récupérer l'utilisateur depuis le token JWT
        user = get_user_from_request(request)
        
        if not user:
            return Response(
                {"error": "Utilisateur non authentifié"}, 
                status=401
            )
        
        # Récupérer le devis (vérifier qu'il appartient bien à l'utilisateur)
        devis = ProjetDevis.objects.get(id=devis_id, user=request.user)
        
        # Supprimer le devis (les matériaux seront supprimés automatiquement à cause de on_delete=CASCADE)
        devis.delete()
        
        return Response(
            {"message": "Devis supprimé avec succès"}, 
            status=200
        )
        
    except ProjetDevis.DoesNotExist:
        return Response(
            {"error": "Devis non trouvé"}, 
            status=404
        )
    except Exception as e:
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": str(e)}, 
            status=400
        )