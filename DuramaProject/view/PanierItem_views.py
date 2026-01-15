from ..models import ContenuPanier, Panier
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..serializer import PanierItemSerialized


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def panier_items(request):
    """
    - GET  : Récupérer tous les items du panier actif de l'utilisateur connecté
    - POST : Ajouter un produit dans le panier actif
    """
    
    # Récupérer ou créer le panier actif
    panier, _ = Panier.objects.get_or_create(user=request.user, actif=True)

    if request.method == 'GET':
        items = ContenuPanier.objects.filter(panier=panier)
        serializer = PanierItemSerialized(items, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        print("=== PANIER ITEMS POST ===")
        print(f"User: {request.user}")
        print(f"Request data: {request.data}")
        
        # 1. Récupérer les données
        produit_id = request.data.get('produit_id')
        produit_variable_id = request.data.get('produit_variable_id')
        attributs_ids = request.data.get('attributs_ids', [])
        quantite = int(request.data.get('quantite', 1))
        is_variable = request.data.get('is_variable', False)
        
        # Conversion de attributs_ids si nécessaire
        if isinstance(attributs_ids, str):
            import json
            try:
                attributs_ids = json.loads(attributs_ids)
            except json.JSONDecodeError:
                import ast
                try:
                    attributs_ids = ast.literal_eval(attributs_ids)
                except:
                    attributs_ids = []
        
        print(f"Produit ID: {produit_id}")
        print(f"Attributs IDs: {attributs_ids}")
        print(f"Quantité: {quantite}")
        
        # 2. VÉRIFICATION DE DUPLICATION
        # Chercher les items existants avec le même produit
        items_existants = ContenuPanier.objects.filter(
            panier=panier,
            produit_id=produit_id
        )
        
        if produit_variable_id:
            items_existants = items_existants.filter(produit_variable_id=produit_variable_id)
        else:
            items_existants = items_existants.filter(produit_variable__isnull=True)
        
        # Convertir attributs_ids en set pour comparaison
        attributs_ids_set = set(map(int, attributs_ids)) if attributs_ids else set()
        
        item_existant = None
        for item in items_existants:
            # Récupérer les attributs de l'item existant
            item_attributs_ids = set(item.attributs.values_list('id', flat=True))
            
            # Comparer les attributs
            if item_attributs_ids == attributs_ids_set:
                item_existant = item
                break
        
        # 3. SI L'ITEM EXISTE DÉJÀ
        if item_existant:
            print(f"Produit existant trouvé, ID: {item_existant.id}")
            print(f"Quantité avant: {item_existant.quantite}")
            print(f"Quantité à ajouter: {quantite}")
            
            # Augmenter la quantité
            item_existant.quantite += quantite
            item_existant.save()
            
            print(f"Quantité après: {item_existant.quantite}")
            
            # Retourner l'item mis à jour
            serializer = PanierItemSerialized(item_existant, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        # 4. SI L'ITEM N'EXISTE PAS - CRÉATION
        print("Création d'un nouvel item")
        
        # Préparer les données pour le serializer
        data = {
            'produit_id': produit_id,
            'quantite': quantite,
            'is_variable': is_variable,
            'panier': panier.id,
            'attributs_ids': attributs_ids
        }
        
        if produit_variable_id:
            data['produit_variable_id'] = produit_variable_id
        
        print(f"Data pour serializer: {data}")
        
        # Créer le serializer
        serializer = PanierItemSerialized(data=data, context={'request': request})
        
        if serializer.is_valid():
            print("Serializer valide")
            print(f"Validated data: {serializer.validated_data}")
            
            try:
                item = serializer.save()
                print(f"Item créé avec ID: {item.id}")
                print(f"Attributs ajoutés: {item.attributs.count()}")
                
                # Retourner la réponse
                response_serializer = PanierItemSerialized(item, context={'request': request})
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                print(f"Erreur lors de la création: {str(e)}")
                import traceback
                traceback.print_exc()
                return Response(
                    {"error": f"Erreur lors de la création: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            print(f"Erreurs du serializer: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deuxElementsDuPanier(request):
    panier, _ = Panier.objects.get_or_create(user=request.user, actif=True)
    contenu = ContenuPanier.objects.filter(panier=panier).order_by('-created_at')[:2]
    serializer = PanierItemSerialized(contenu, many=True)
    return Response(serializer.data)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def panier_item_detail(request, pk):
    panier, _ = Panier.objects.get_or_create(user=request.user, actif=True)
    try:
        item = ContenuPanier.objects.get(pk=pk, panier=panier)
    except ContenuPanier.DoesNotExist:
        return Response(
            {"error": "Item non trouvé dans le panier actif"}, 
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        serializer = PanierItemSerialized(item, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        
        # DEBUG
        print(f"=== PANIER ITEM DETAIL {'PATCH' if partial else 'PUT'} ===")
        print(f"Item ID: {item.id}")
        print(f"Request data: {request.data}")
        
        # Préparer les données
        data = request.data.copy()
        
        # Toujours inclure le panier dans les données
        data['panier'] = panier.id
        
        # Convertir attributs_ids si nécessaire
        attributs_ids = data.get('attributs_ids', [])
        if isinstance(attributs_ids, str):
            import json
            try:
                attributs_ids = json.loads(attributs_ids)
            except json.JSONDecodeError:
                import ast
                try:
                    attributs_ids = ast.literal_eval(attributs_ids)
                except:
                    attributs_ids = []
        data['attributs_ids'] = attributs_ids
        
        print(f"attributs_ids après conversion: {attributs_ids}")
        
        serializer = PanierItemSerialized(
            item, 
            data=data, 
            partial=partial, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            print("Serializer valide")
            print(f"Validated data keys: {serializer.validated_data.keys()}")
            
            # IMPORTANT: Ne pas gérer les attributs manuellement
            # Le serializer le fait grâce à source='attributs'
            updated_item = serializer.save()
            
            print(f"Item mis à jour ID: {updated_item.id}")
            print(f"Attributs après mise à jour: {updated_item.attributs.count()}")
            
            # Retourner la réponse
            response_serializer = PanierItemSerialized(updated_item, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        print(f"Erreurs du serializer: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        item.delete()
        return Response(
            {"message": "Item supprimé du panier"}, 
            status=status.HTTP_204_NO_CONTENT
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def total_panier(request):
    panier, _ = Panier.objects.get_or_create(user=request.user, actif=True)
    contenu = ContenuPanier.objects.filter(panier=panier)

    total = 0
    for item in contenu:
        prix = item.produit.prix_promo if item.produit.prix_promo else item.produit.prix_vente
        total += prix * item.quantite

    return Response(total, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def augmenter_quantite(request, pk):
    try:
        item = ContenuPanier.objects.get(pk=pk)
    except ContenuPanier.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    item.quantite += 1
    item.save()
    return Response({"message": "Quantité mise à jour avec succès ✅"})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dimunuer_quantite(request, pk):
    try:
        item = ContenuPanier.objects.get(pk=pk)
    except ContenuPanier.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if item.quantite > 1:
        item.quantite -= 1
        item.save()
    return Response({"message": "Quantité mise à jour avec succès ✅"})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def supprimer_item(request, pk):
    try:
        item = ContenuPanier.objects.get(pk=pk)
    except ContenuPanier.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    item.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def vider_panier(request):
    panier, _ = Panier.objects.get_or_create(user=request.user, actif=True)
    items = ContenuPanier.objects.filter(panier=panier)

    if not items.exists():
        return Response({"message": "Le panier est déjà vide 🧺"}, status=status.HTTP_200_OK)
    items.delete()
    return Response({"message": "Le panier a été vidé avec succès 🧹"}, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nombre_element_panier(request):
    try:
        panier = Panier.objects.get(user=request.user, actif=True)
    except Panier.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    items_nombre = ContenuPanier.objects.filter(panier=panier).count()
    return Response(items_nombre)
